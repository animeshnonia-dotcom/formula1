import math
import numpy as np
import osmnx as ox
import networkx as nx
from sklearn.cluster import KMeans
from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def build_road_graph(city="Hyderabad, India"):
    G = ox.graph_from_place(city, network_type="drive")
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    return G

def road_travel_time(G, lat1, lon1, lat2, lon2):
    orig = ox.nearest_nodes(G, lon1, lat1)
    dest = ox.nearest_nodes(G, lon2, lat2)
    return nx.shortest_path_length(G, orig, dest, weight="travel_time")

def cluster_gvps(gvps, k):
    coords = np.array([[g["lat"], g["lon"]] for g in gvps])
    labels = KMeans(n_clusters=k, random_state=42).fit_predict(coords)

    clusters = {}
    for i, label in enumerate(labels):
        clusters.setdefault(label, []).append(gvps[i])
    return clusters

def assign_sctp(cluster, sctps):
    clat = sum(g["lat"] for g in cluster) / len(cluster)
    clon = sum(g["lon"] for g in cluster) / len(cluster)

    def hav(lat1, lon1, lat2, lon2):
        R = 6371
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2 * R * math.asin(math.sqrt(a))

    return min(sctps, key=lambda s: hav(clat, clon, s["lat"], s["lon"]))

def create_cluster_data(cluster, sctp, vehicles, G):
    locations = [(sctp["lat"], sctp["lon"])]
    demands = [0]
    time_windows = [(0, vehicles[0]["shift_time"])]

    for g in cluster:
        locations.append((g["lat"], g["lon"]))
        demands.append(g["waste"])
        time_windows.append(g["time_window"])

    time_matrix = []
    for a in locations:
        row = []
        for b in locations:
            t = road_travel_time(G, a[0], a[1], b[0], b[1])
            row.append(int(t / 60))  # minutes
        time_matrix.append(row)

    return {
        "time_matrix": time_matrix,
        "demands": demands,
        "time_windows": time_windows,
        "vehicle_capacities": [v["capacity"] for v in vehicles],
        "shift_time": vehicles[0]["shift_time"],
        "num_vehicles": len(vehicles),
        "depot": 0
    }

def solve_vrptw(data):
    manager = pywrapcp.RoutingIndexManager(
        len(data["time_matrix"]),
        data["num_vehicles"],
        data["depot"]
    )

    routing = pywrapcp.RoutingModel(manager)

    def time_cb(i, j):
        return data["time_matrix"][
            manager.IndexToNode(i)
        ][
            manager.IndexToNode(j)
        ]

    transit = routing.RegisterTransitCallback(time_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)

    def demand_cb(i):
        return data["demands"][manager.IndexToNode(i)]

    demand = routing.RegisterUnaryTransitCallback(demand_cb)

    routing.AddDimensionWithVehicleCapacity(
        demand, 0, data["vehicle_capacities"], True, "Capacity"
    )

    routing.AddDimension(
        transit,
        30,
        data["shift_time"],
        False,
        "Time"
    )

    time_dim = routing.GetDimensionOrDie("Time")

    for node, window in enumerate(data["time_windows"]):
        index = manager.NodeToIndex(node)
        time_dim.CumulVar(index).SetRange(window[0], window[1])

    for v in range(data["num_vehicles"]):
        time_dim.CumulVar(routing.End(v)).SetRange(0, data["shift_time"])

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = 15

    solution = routing.SolveWithParameters(params)
    return routing, manager, solution

def extract_routes(routing, manager, solution):
    routes = {}
    if not solution:
        return routes

    for v in range(routing.vehicles()):
        index = routing.Start(v)
        route = []
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route.append(manager.IndexToNode(index))
        routes[v] = route

    return routes

if __name__ == "__main__":

    # ----------------------------
    # INPUT DATA
    # ----------------------------

    gvps = [
        {"lat":17.385, "lon":78.4867, "waste":300, "time_window":(0,240)},
        {"lat":17.39,  "lon":78.49,   "waste":200, "time_window":(120,360)},
        {"lat":17.38,  "lon":78.48,   "waste":150, "time_window":(0,480)},
        {"lat":17.37,  "lon":78.47,   "waste":180, "time_window":(60,300)},
        {"lat":17.41,  "lon":78.51,   "waste":220, "time_window":(0,480)},
    ]

    sctps = [
        {"lat":17.40, "lon":78.50},
        {"lat":17.36, "lon":78.46},
    ]

    vehicles = [
        {"capacity":600, "shift_time":480},
        {"capacity":600, "shift_time":480},
    ]

    # ----------------------------
    # RUN PIPELINE
    # ----------------------------

    G = build_road_graph("Hyderabad, India")
    clusters = cluster_gvps(gvps, k=2)

    for cid, cluster in clusters.items():
        sctp = assign_sctp(cluster, sctps)
        data = create_cluster_data(cluster, sctp, vehicles, G)
        routing, manager, solution = solve_vrptw(data)
        routes = extract_routes(routing, manager, solution)

        print(f"\nCluster {cid} | Assigned SCTP: {sctp}")
        for v, r in routes.items():
            print(f" Vehicle {v}: {r}")
