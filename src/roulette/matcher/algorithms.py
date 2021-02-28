from dataclasses import dataclass, field
import math
from typing import Dict, List, Tuple
from django.conf import settings
import time
import random
from queue import Queue
from enum import Enum
from .models import Match, MatchColor, MatchQuality, MatchingGraph, PenaltyInfo, RouletteUser


def merge_matches(matches: List[Match]) -> List[List[RouletteUser]]:
    graph: Dict[str, Tuple[RouletteUser, List[RouletteUser]]] = {}
    for match in matches:
        user, neighbors = graph.get(str(match.user_a.id), (match.user_a, []))
        neighbors.append(match.user_b)
        graph[str(user.id)] = (user, neighbors)
        user, neighbors = graph.get(str(match.user_b.id), (match.user_b, []))
        neighbors.append(match.user_a)
        graph[str(user.id)] = (user, neighbors)
    groups = []
    visited_ids = set()
    # BFS search through graph to form connected components (groups)
    for (user, _) in graph.values():
        group = []
        q: Queue[RouletteUser] = Queue()
        q.put(user)
        while not q.empty():
            u = q.get()
            if u.id in visited_ids:
                continue
            visited_ids.add(u.id)
            group.append(u)
            for neighbor in graph[str(u.id)][1]:
                q.put(neighbor)
        if len(group) > 0:
            groups.append(group)
    return groups


@dataclass
class Matching():
    matches: List[Tuple[RouletteUser, ...]] = field(default_factory=list)
    total_penalty: float = 0.0


def generate_matches_montecarlo(graph: MatchingGraph, penalty_for_grouping_with_forbidden_user: float) -> Matching:
    if len(graph) <= 1:
        return Matching()  # Not enough users
    best_matching = Matching()
    best_matching.total_penalty = math.inf
    timeout_seconds = settings.MATCHER_MONTECARLO_TIMEOUT_MS / 1000.0
    end_after = time.monotonic() + timeout_seconds
    has_time = True
    iterations = 0
    while has_time:
        iterations += 1
        not_processed_nodes = graph[:]
        processed_user_ids = set()
        random.shuffle(not_processed_nodes)
        singleton_user_ids = set()
        matches: List[List[RouletteUser]] = []
        total_penalty = 0.0
        while len(not_processed_nodes) > 0:
            (user, neighbors) = not_processed_nodes[-1]
            not_processed_nodes.pop()
            if user.id in processed_user_ids:
                # Already processed, but not removed from the list because it would be time-expensive.
                continue
            processed_user_ids.add(user.id)
            possible_matches = [(user2, weight) for (
                user2, weight, _) in neighbors if user2.id not in processed_user_ids]
            if len(possible_matches) == 0:
                singleton_user_ids.add(user.id)
            else:
                (user2, weight) = random.sample(possible_matches, 1)[0]
                processed_user_ids.add(user2.id)
                # List, not tuple, because we could modify it later
                matches.append([user, user2])
                total_penalty += weight
        # Add non-paired users to the groups randomly
        for (user, neighbors) in graph:
            if user.id not in singleton_user_ids:
                continue
            if len(matches) == 0:
                # No users matched at all? Then create an artificial group
                matches.append([user])
            else:
                random_group = random.choice(matches)
                for group_user in random_group:
                    edge_exists = False
                    for (user2, weight, _) in neighbors:
                        if group_user.id == user2.id:
                            total_penalty += weight
                            edge_exists = True
                    if not edge_exists:
                        # Add a penalty for grouping with a user that otherwise would be forbidden (but we have to assign him somewhere)
                        total_penalty += penalty_for_grouping_with_forbidden_user
                random_group.append(user)
        # Convert lists back to tuples
        solution = [tuple(l) for l in matches]
        if total_penalty < best_matching.total_penalty:
            best_matching.matches = solution
            best_matching.total_penalty = total_penalty
        if time.monotonic() > end_after:
            has_time = False
    print("iterations: " + str(iterations))
    return best_matching


def get_matches_quality(graph: MatchingGraph, matches: List[Tuple[RouletteUser, ...]], penalty_for_grouping_with_forbidden_user, green_percentile_threshold=settings.MATCHER_GREEN_PERCENTILE, yellow_percentile_threshold=settings.MATCHER_YELLOW_PERCENTILE) -> List[MatchQuality]:
    """
    Calculate quality of each match in matches.
    graph: Graph in format: [(user1, [(user2, weight, penalty_info), ...]), ...]
    matches: A list of tuples of users matched with each other.
    penalty_for_grouping_with_forbidden_user: penalty for taking edge that doesn't exist in the graph
    green_percentile_threshold: a float threshold that tells how many edges in the graph are not green (yellow or red). If none, a default from settings.MATCHER_GREEN_PERCENTILE will be used.
    yellow_percentile_threshold: a float threshold that tells how many edges in the graph are  green or yellow (not red). If none, a default from settings.MATCHER_YELLOW_PERCENTILE will be used.
    Returns: a list of MatchQuality objects, for each match in matches.
    """

    def get_graph_weights():
        graph_weights = []
        for _, edges in graph:
            for _, weight, _ in edges:
                graph_weights.append(weight)
        graph_weights.sort()
        return graph_weights

    # Return the maximum weight, for an edge to belong to a percentile.
    def get_threshold(percentile, graph_weights):
        threshold_index = math.ceil(
            len(graph_weights) * percentile / 100.0) - 1
        if threshold_index < 0:
            return -math.inf
        if threshold_index >= len(graph_weights):
            return math.inf
        return graph_weights[threshold_index]

    # Return the graph dictionary: { user_id -> (user, edges) }
    # where edges is a list of (user_b, weight, penalty_info).
    def get_graph_as_dict(graph_list):
        graph_dict = {}
        for user, edges in graph_list:
            graph_dict[user.id] = (user, edges)
        return graph_dict

    def get_color(weight, green_threshold, yellow_threshold):
        if weight <= green_threshold:
            return MatchColor.GREEN
        if weight <= yellow_threshold:
            return MatchColor.YELLOW
        return MatchColor.RED

    def get_all_pairs(match_set):
        return [(user_a, user_b) for user_a in match_set for user_b in match_set if user_a.id < user_b.id]

    graph_weights = get_graph_weights()
    green_threshold = get_threshold(
        green_percentile_threshold, graph_weights)
    yellow_threshold = get_threshold(
        yellow_percentile_threshold, graph_weights)
    graph_dict = get_graph_as_dict(graph)
    match_qualities = []

    for match in matches:
        match_quality = MatchQuality()
        for user_a, user_b in get_all_pairs(match):
            match_quality.users_a.append(user_a)
            match_quality.users_b.append(user_b)
            edge_found = False
            for user, weight, penalty_info in graph_dict[user_a.id][1]:
                if user.id == user_b.id:
                    edge_found = True
                    match_quality.penalty_infos.append(penalty_info)
                    color = get_color(
                        weight, green_threshold, yellow_threshold)
                    if match_quality.color is None or match_quality.color.value < color.value:
                        match_quality.color = color
                    break
            if not edge_found:
                penalty_info = PenaltyInfo(
                    is_forbidden=True, forbidden_penalty=penalty_for_grouping_with_forbidden_user)
                match_quality.penalty_infos.append(penalty_info)
        match_qualities.append(match_quality)

    return match_qualities
