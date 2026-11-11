import collections
import heapq
import math

import carla

ROUTE_STEP_M = 2.0            # Khoảng cách giữa 2 điểm liên tiếp của lộ trình
BRANCH_LOOKAHEAD_M = 20.0     # Nhìn xa bao nhiêu mét để so sánh các nhánh ở ngã tư


def angle_diff(a, b):
    # Hiệu hai góc (độ), đưa về khoảng -180..180
    return (a - b + 180.0) % 360.0 - 180.0


def choose_branch(wp, branches):
    """Ở ngã tư wp.next trả về nhiều nhánh (thẳng, rẽ, quay đầu). Chọn nhánh đi thẳng nhất.

    Mỗi nhánh được đi tiếp BRANCH_LOOKAHEAD_M mét rồi đo góc lệch của đường nối từ wp tới điểm đó
    so với hướng hiện tại. Nhìn xa thì nhánh quay đầu lệch rất nhiều, không bị nhầm như khi chỉ nhìn 2 m.
    """
    if len(branches) == 1:
        return branches[0]

    def turn_angle(branch):
        far = branch
        for _ in range(int(BRANCH_LOOKAHEAD_M / ROUTE_STEP_M) - 1):
            nxt = far.next(ROUTE_STEP_M)
            if not nxt:
                break
            far = nxt[0]
        d = far.transform.location - wp.transform.location
        return abs(angle_diff(math.degrees(math.atan2(d.y, d.x)), wp.transform.rotation.yaw))

    return min(branches, key=turn_angle)


class LoTrinh:
    """Lộ trình chung: danh sách waypoint cách nhau ROUTE_STEP_M, tạo một lần trước khi chạy.

    Có hai kiểu:
    - LoTrinh.thang: đi thẳng về phía trước (và lùi về phía sau) từ điểm xuất phát, hết đường thì dừng.
    - LoTrinh.tham_quan: vòng khép kín đi qua gần hết các đoạn đường của bản đồ, chạy mãi không hết.

    Vị trí trên lộ trình (waypoint_at) tính bằng mét từ điểm xuất phát: dương là phía trước, âm là phía sau.
    Lộ trình khép kín thì sau điểm cuối là điểm đầu, nên mọi chỉ số tính theo modulo.
    """

    def __init__(self, waypoints, start_idx=0, closed=False):
        self.waypoints = waypoints
        self.start_idx = start_idx                  # điểm xuất phát nằm ở chỉ số này
        self.closed = closed
        self.locations = [w.transform.location for w in waypoints]
        self.stats = {}

    @classmethod
    def thang(cls, start_wp, length_m, back_m=0.0):
        """Đi thẳng length_m mét phía trước và back_m mét phía sau điểm xuất phát."""
        forward = [start_wp]
        while len(forward) * ROUTE_STEP_M < length_m:
            branches = forward[-1].next(ROUTE_STEP_M)
            if not branches:
                break   # hết đường
            forward.append(choose_branch(forward[-1], branches))

        # Đi lùi bằng previous(). Ở chỗ nhập đường có nhiều nhánh đi tới, chọn nhánh cùng hướng nhất
        back = []
        wp = start_wp
        while len(back) * ROUTE_STEP_M < back_m:
            previous = wp.previous(ROUTE_STEP_M)
            if not previous:
                break
            wp = min(previous, key=lambda c: abs(angle_diff(c.transform.rotation.yaw, wp.transform.rotation.yaw)))
            back.append(wp)
        return cls(back[::-1] + forward, start_idx=len(back))

    @classmethod
    def tham_quan(cls, carla_map, start_wp):
        """Vòng khép kín đi qua gần hết các đoạn đường, bắt đầu và kết thúc tại start_wp."""
        waypoints, stats = build_tour(carla_map, start_wp)
        route = cls(waypoints, start_idx=0, closed=True)
        route.stats = stats
        return route

    @property
    def length(self):
        return len(self.waypoints) * ROUTE_STEP_M if self.closed else (len(self.waypoints) - 1) * ROUTE_STEP_M

    def index_at(self, s):
        # Chỉ số điểm cách điểm xuất phát s mét (âm là phía sau). Vòng khép kín thì quay vòng, lộ trình thẳng thì phải nằm trong đường
        i = self.start_idx + int(round(s / ROUTE_STEP_M))
        if self.closed:
            return i % len(self.waypoints)
        if not 0 <= i < len(self.waypoints):
            raise RuntimeError(
                f"Vị trí {s} m nằm ngoài lộ trình (từ {-self.start_idx * ROUTE_STEP_M:.0f} m "
                f"đến {(len(self.waypoints) - 1 - self.start_idx) * ROUTE_STEP_M:.0f} m tính từ điểm xuất phát)")
        return i

    def waypoint_at(self, s):
        return self.waypoints[self.index_at(s)]

    def nearest_index(self, location, start=0, window=None):
        # Điểm gần xe nhất. Tìm trong cửa sổ tính từ start để chỉ đi tới, không nhảy ngược
        n = len(self.locations)
        if window is None:
            candidates = range(n)
        elif self.closed:
            candidates = [(start + k) % n for k in range(window)]
        else:
            candidates = range(start, min(start + window, n))
        return min(candidates, key=lambda i: location.distance(self.locations[i]))

    def turning_summary(self, window_m=20.0):
        """(tổng góc đổi hướng, góc đổi hướng lớn nhất trong một đoạn window_m mét), đơn vị độ."""
        yaws = [w.transform.rotation.yaw for w in self.waypoints]
        n = int(window_m / ROUTE_STEP_M)
        total = sum(abs(angle_diff(yaws[i], yaws[i - 1])) for i in range(1, len(yaws)))
        worst = max((abs(angle_diff(yaws[i + n], yaws[i])) for i in range(len(yaws) - n)), default=0.0)
        return total, worst


def make_route(carla_map, start_wp, cfg_route):
    """Dựng lộ trình theo mục lo_trinh trong YAML (kieu: thang hoặc tham_quan), bắt đầu từ start_wp."""
    if cfg_route.get('kieu', 'thang') == 'tham_quan':
        return LoTrinh.tham_quan(carla_map, start_wp)
    return LoTrinh.thang(start_wp, cfg_route.get('chieu_dai', 600.0), cfg_route.get('doan_lui', 50.0))


def lane_shift(wp, n):
    """Làn cùng chiều cách wp n làn (âm là sang trái, dương là sang phải). Không có làn lái xe đó thì trả về None."""
    lane = wp
    for _ in range(abs(n)):
        lane = lane.get_right_lane() if n > 0 else lane.get_left_lane()
        if lane is None or lane.lane_type != carla.LaneType.Driving or lane.lane_id * wp.lane_id < 0:
            return None
    return lane


def opposite_lane(wp):
    """Làn xe chạy NGƯỢC chiều gần nhất (bên kia vạch giữa đường), không có thì trả về None.

    Đi sang trái từng làn. Khi đã sang phía ngược chiều thì "trái" của các làn bên đó lại quay về phía mình,
    nên từ đó đi tiếp bằng get_right_lane() để ra xa. Bỏ qua lề, dải phân cách cho tới khi gặp làn Driving.
    """
    lane, crossed = wp, False
    for _ in range(10):
        lane = lane.get_right_lane() if crossed else lane.get_left_lane()
        if lane is None:
            return None
        if lane.lane_id * wp.lane_id < 0:
            crossed = True
            if lane.lane_type == carla.LaneType.Driving:
                return lane
    return None


# ================== VÒNG THAM QUAN: ĐI QUA GẦN HẾT CÁC ĐOẠN ĐƯỜNG CỦA BẢN ĐỒ ==================
# Mạng đường của CARLA là đồ thị có hướng: mỗi "đoạn" là một làn nằm giữa 2 điểm rẽ nhánh
# (carla_map.get_topology()). Vòng tham quan là một đường đi khép kín đi qua mọi đoạn ít nhất một lần.

def _point_key(wp):
    # Hai điểm cách nhau dưới 1 m coi là trùng, dùng để nối đoạn này với đoạn kế tiếp
    location = wp.transform.location
    return round(location.x), round(location.y)


def _segment_graph(carla_map):
    """Đồ thị các đoạn đường: segments[i] = (waypoint vào, waypoint ra), successors[i] = các đoạn đi tiếp."""
    segments = carla_map.get_topology()
    starting_at = collections.defaultdict(list)
    for i, (entry, _) in enumerate(segments):
        starting_at[_point_key(entry)].append(i)
    successors = {i: list(starting_at.get(_point_key(exit_wp), [])) for i, (_, exit_wp) in enumerate(segments)}
    return segments, successors


def _chord_distance(location, entry, exit_wp):
    # Khoảng cách từ một điểm tới đoạn thẳng nối điểm vào và điểm ra của đoạn đường
    a, b = entry.transform.location, exit_wp.transform.location
    ab = b - a
    denom = ab.x * ab.x + ab.y * ab.y
    t = 0.0 if denom == 0 else max(0.0, min(1.0, ((location.x - a.x) * ab.x + (location.y - a.y) * ab.y) / denom))
    return location.distance(carla.Location(a.x + t * ab.x, a.y + t * ab.y, a.z))


def _find_segment(segments, wp):
    """Đoạn chứa waypoint wp: cùng đường, cùng làn, và gần đường nối hai đầu đoạn nhất.

    Không dựa vào s vì các đoạn trong ngã tư được CARLA ghi s bằng 0 ở cả hai đầu.
    """
    candidates = [i for i, (entry, _) in enumerate(segments) if (entry.road_id, entry.lane_id) == (wp.road_id, wp.lane_id)]
    if not candidates:
        return None
    location = wp.transform.location
    return min(candidates, key=lambda i: _chord_distance(location, *segments[i]))


def _walk(wp, stop_location, max_m=2000.0):
    """Đi từ wp bằng next() cho tới khi cách stop_location dưới 1 bước, trả về danh sách waypoint."""
    points = [wp]
    while wp.transform.location.distance(stop_location) > ROUTE_STEP_M and len(points) * ROUTE_STEP_M < max_m:
        branches = wp.next(ROUTE_STEP_M)
        if not branches:
            break
        wp = choose_branch(wp, branches)
        points.append(wp)
    return points


def _reachable_both_ways(successors, start):
    # Các đoạn vừa đi tới được từ start, vừa quay về được start (cùng một thành phần liên thông mạnh)
    def reach(adj):
        seen, stack = {start}, [start]
        while stack:
            for nxt in adj.get(stack.pop(), []):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen
    reverse = collections.defaultdict(list)
    for u, vs in successors.items():
        for v in vs:
            reverse[v].append(u)
    return reach(successors) & reach(reverse)


def _min_cost_transport(supply, demand, cost):
    """Bài toán vận chuyển chi phí nhỏ nhất, giải bằng luồng chi phí nhỏ nhất (đường tăng ngắn nhất lặp lại).

    supply: {nguồn: số đơn vị}, demand: {đích: số đơn vị}, cost[(nguồn, đích)]: chi phí một đơn vị.
    Trả về danh sách (nguồn, đích), mỗi phần tử là một đơn vị hàng được chuyển.
    """
    SRC, DST = ('nguon',), ('dich',)
    graph = collections.defaultdict(dict)   # graph[u][v] = [sức chứa còn lại, chi phí]

    def add(u, v, capacity, c):
        graph[u][v] = [capacity, c]
        graph[v].setdefault(u, [0, -c])     # cạnh ngược trong đồ thị dư

    for u, amount in supply.items():
        add(SRC, u, amount, 0.0)
    for v, amount in demand.items():
        add(v, DST, amount, 0.0)
    for (u, v), c in cost.items():
        add(u, v, math.inf, c)

    pairs = []
    while True:
        # Bellman-Ford: đường đi chi phí nhỏ nhất từ SRC tới DST trong đồ thị dư (có cạnh chi phí âm)
        dist, parent = {SRC: 0.0}, {}
        for _ in range(len(graph)):
            changed = False
            for u in list(dist):
                for v, (capacity, c) in graph[u].items():
                    if capacity > 0 and dist[u] + c < dist.get(v, math.inf) - 1e-9:
                        dist[v], parent[v] = dist[u] + c, u
                        changed = True
            if not changed:
                break
        if DST not in dist:
            return pairs
        # Đẩy một đơn vị dọc theo đường vừa tìm
        path, v = [], DST
        while v != SRC:
            path.append((parent[v], v))
            v = parent[v]
        for u, v in path:
            graph[u][v][0] -= 1
            graph[v][u][0] += 1
        pairs = []
        for u in supply:
            for v, (capacity, c) in graph[u].items():
                if v in demand and c >= 0:
                    flow = graph[v][u][0]             # luồng trên cạnh u -> v bằng sức chứa của cạnh ngược
                    pairs += [(u, v)] * flow


def build_tour(carla_map, start_wp):
    """Dựng vòng tham quan khép kín đi qua mọi con đường của mạng chính (mỗi chiều đi một lần), ngắn nhất có thể.

    Đây là bài toán người đưa thư nông thôn có hướng (Directed Rural Postman):
    0. Mỗi đoạn đường là một cạnh có hướng, đỉnh là điểm nối giữa các đoạn. Chỉ một số đoạn là BẮT BUỘC:
       mỗi con đường, mỗi chiều đi chọn một làn (làn ngoài cùng bên phải). Làn trong ngã tư và các làn
       song song còn lại là TÙY CHỌN, chỉ dùng để nối khi cần, nên xe không phải đi lại một đường nhiều lần.
    1. Các đoạn bắt buộc rời rạc thành nhiều cụm: nối các cụm thành một vòng bằng đường ngắn nhất,
       mỗi bước đi tới cụm chưa nối gần nhất (láng giềng gần nhất).
    2. Vòng đi qua mỗi cạnh đúng một lần chỉ có khi mọi đỉnh có số cạnh vào bằng số cạnh ra.
       Đỉnh nào lệch thì phải đi thêm đường. Chọn đường đi thêm sao cho tổng mét nhỏ nhất: bài toán
       vận chuyển giữa đỉnh thừa cạnh vào và đỉnh thừa cạnh ra, chi phí là đường ngắn nhất giữa chúng
       (Dijkstra), giải bằng luồng chi phí nhỏ nhất.
    3. Mọi đỉnh đã cân bằng và liên thông: thuật toán Hierholzer dựng vòng đi qua mỗi cạnh đúng một lần.
    Trả về (danh sách waypoint, thông tin thống kê).
    """
    segments, successors = _segment_graph(carla_map)
    first = _find_segment(segments, start_wp)
    if first is None:
        raise RuntimeError("Điểm xuất phát không nằm trên đoạn đường nào của bản đồ")
    network = _reachable_both_ways(successors, first)
    if len(network) < 20:
        raise RuntimeError(f"Điểm xuất phát nằm trong một vòng riêng chỉ có {len(network)} đoạn, "
                           "không nối được sang phần còn lại của bản đồ")

    # Waypoint và độ dài thật (theo đường đi, không phải đường chim bay) của từng đoạn
    points = {i: _walk(segments[i][0], segments[i][1].transform.location) for i in network}
    length = {i: len(points[i]) * ROUTE_STEP_M for i in network}

    def tail(i):
        return _point_key(segments[i][0])

    def head(i):
        return _point_key(segments[i][1])

    out_edges = collections.defaultdict(list)
    for i in network:
        out_edges[tail(i)].append(i)

    def dijkstra(source):
        # Đường ngắn nhất (mét) từ đỉnh source tới mọi đỉnh, trả về khoảng cách và cạnh cuối của đường đi
        dist, last_edge, heap = {source: 0.0}, {}, [(0.0, source)]
        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u]:
                continue
            for i in out_edges[u]:
                v = head(i)
                if d + length[i] < dist.get(v, math.inf):
                    dist[v], last_edge[v] = d + length[i], i
                    heapq.heappush(heap, (dist[v], v))
        return dist, last_edge

    def path_edges(source, target, last_edge):
        # Dựng lại danh sách đoạn của đường ngắn nhất source -> target từ kết quả Dijkstra
        node, path = target, []
        while node != source:
            path.append(last_edge[node])
            node = tail(last_edge[node])
        return path[::-1]

    # 0) Đoạn bắt buộc: mỗi (đường, đoạn, chiều đi) chọn làn ngoài cùng bên phải, cộng đoạn chứa điểm xuất phát
    groups = collections.defaultdict(list)
    for i in network:
        entry = segments[i][0]
        if not entry.is_junction:
            groups[(entry.road_id, entry.section_id, entry.lane_id > 0)].append(i)
    required = {first} | {max(lanes, key=lambda i: abs(segments[i][0].lane_id)) for lanes in groups.values()}
    edges = list(required)

    # 1) Nối các cụm đoạn bắt buộc thành một khối: đi từ cụm hiện tại tới cụm chưa nối gần nhất, cuối cùng quay về
    def clusters(edge_list):
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for i in edge_list:
            parent[find(tail(i))] = find(head(i))
        groups_of = collections.defaultdict(set)
        for i in edge_list:
            groups_of[find(tail(i))].update((tail(i), head(i)))
        return list(groups_of.values())

    parts = clusters(edges)
    if len(parts) > 1:
        from_node = {}
        start_part = next(part for part in parts if tail(first) in part)
        current, remaining = start_part, [part for part in parts if part is not start_part]
        while remaining:
            best = None
            for u in current:
                dist, last_edge = from_node.setdefault(u, dijkstra(u))
                for part in remaining:
                    for v in part:
                        if v in dist and (best is None or dist[v] < best[0]):
                            best = (dist[v], u, v, part)
            _, u, v, part = best
            edges += path_edges(u, v, from_node[u][1])
            current = part
            remaining.remove(part)
        # quay về cụm xuất phát để khép vòng
        best = None
        for u in current:
            dist, last_edge = from_node.setdefault(u, dijkstra(u))
            for v in start_part:
                if v in dist and (best is None or dist[v] < best[0]):
                    best = (dist[v], u, v)
        edges += path_edges(best[1], best[2], from_node[best[1]][1])

    # 2) Độ lệch của từng đỉnh: số cạnh ra trừ số cạnh vào
    balance = collections.Counter()
    for i in edges:
        balance[tail(i)] += 1
        balance[head(i)] -= 1
    need_out = {v: -b for v, b in balance.items() if b < 0}   # thừa cạnh vào: phải đi thêm đường BẮT ĐẦU từ đây
    need_in = {v: b for v, b in balance.items() if b > 0}     # thừa cạnh ra: phải đi thêm đường KẾT THÚC ở đây

    # Chọn đường đi thêm: vận chuyển chi phí nhỏ nhất từ need_out sang need_in
    shortest = {u: dijkstra(u) for u in need_out}
    cost = {(u, v): shortest[u][0][v] for u in need_out for v in need_in if v in shortest[u][0]}
    duplicated = []
    for u, v in _min_cost_transport(need_out, need_in, cost):
        duplicated += path_edges(u, v, shortest[u][1])

    # 3) Hierholzer: dựng vòng đi qua mỗi cạnh (gồm cả cạnh đi lặp) đúng một lần
    adjacency = collections.defaultdict(list)
    for i in edges + duplicated:
        adjacency[tail(i)].append(i)
    stack, circuit = [(tail(first), None)], []
    while stack:
        node, edge = stack[-1]
        if adjacency[node]:
            nxt = adjacency[node].pop()
            stack.append((head(nxt), nxt))
        else:
            stack.pop()
            if edge is not None:
                circuit.append(edge)
    circuit.reverse()
    k = circuit.index(first)
    order = circuit[k:] + circuit[:k]   # xoay vòng để bắt đầu bằng đoạn chứa điểm xuất phát

    # 4) Đổi chuỗi đoạn thành chuỗi waypoint: đoạn đầu đi từ start_wp, cuối cùng quay về start_wp
    waypoints = _walk(start_wp, segments[first][1].transform.location)
    for index in order[1:]:
        waypoints += points[index]
    waypoints += _walk(segments[first][0], start_wp.transform.location)

    stats = {'doan_trong_mang': len(network), 'doan_bat_buoc': len(required),
             'doan_bat_buoc_da_di': len(required & set(order)), 'doan_da_di': len(set(order)),
             'so_doan_di': len(order), 'tong_duong_mang': sum(length.values()),
             'duong_bat_buoc': sum(length[i] for i in required), 'chieu_dai': len(waypoints) * ROUTE_STEP_M}
    return waypoints, stats
