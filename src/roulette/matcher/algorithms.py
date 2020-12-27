import math
from django.conf import settings
import time
import random
from queue import Queue
from enum import Enum
from .models import RouletteUser


def merge_matches(matches):
    """ Given a list of Matches, returns a list of user tuples (groups) """
    graph = {}  # user_id -> (user, list of users matched with)
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
        q = Queue()
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


def generate_matches_montecarlo(graph, penalty_for_grouping_with_forbidden_user):
    """ Input: Graph in format: [(user1, [(user2, weight, penalty_info), ...]), ...] """
    """ Returns: list of tuples of users """
    if len(graph) <= 1:
        return []  # Not enough users
    best_solution = []
    best_solution_penalty = math.inf
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
        matches = []
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
                (user2, weight, _) = random.sample(possible_matches, 1)[0]
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
        matches = [tuple(l) for l in matches]
        if total_penalty < best_solution_penalty:
            best_solution = matches
            best_solution_penalty = total_penalty
        if time.monotonic() > end_after:
            has_time = False
    print("iterations: " + str(iterations))
    return best_solution

class MatchColor(Enum):
    GREEN = 1
    YELLOW = 2
    RED = 3

class MatchQuality:
    users = ()
    total_weight = 0.0
    color = None

    def description(self) -> str:
        pass


def get_matches_quality(graph, matches, penalty_for_grouping_with_forbidden_user) -> MatchQuality:
    """
    Calculate quality of each match in matches.
    graph: Graph in format: [(user1, [(user2, weight, penalty_info), ...]), ...]
    matches: A list of tuples of users matched with each other.
    penalty_for_grouping_with_forbidden_user: penalty for taking edge that doesn't exist in the graph
    Returns: a list of MatchQuality objects, for each match in matches.
    """
    pass



