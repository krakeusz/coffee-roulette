from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from django.test import TestCase
from django.utils import timezone
from typing import List

from .models import PenaltyInfo, Roulette, Vote, Match, MatchQuality, RouletteUser, ExclusionGroup, PenaltyGroup, PenaltyForPenaltyGroup, PenaltyForNumberOfMatches, PenaltyForRecentMatch, get_last_roulette, matching_graph, MatchColor
from .algorithms import get_matches_quality


def create_positive_numbers_users(n_users):
    for i in range(1, n_users+1):
        RouletteUser.objects.create(name=str(i), email=str(i)+"@example.com")
    return RouletteUser.objects.all()


def create_groups_modulo_k(n_users, k_groups, group_model):
    """
    Creates k_groups exclusion or penalty groups of 'positive natural number users', containing users in the same modulo group.
    For example, if k_groups == 3, n_users == 12, creates 3 groups:
    1, 4, 7, 10
    2, 5, 8, 11
    3, 6, 9, 12
    """
    groups = [group_model.objects.create() for _ in range(k_groups)]
    for i in range(1, n_users+1):
        user = get_object_or_404(RouletteUser, name=str(i))
        groups[i % k_groups].users.add(user)
    for group in groups:
        group.save()
    return groups


def create_match(roulette, user1_id, user2_id):
    Match.objects.create(user_a=get_object_or_404(RouletteUser, pk=user1_id),
                         user_b=get_object_or_404(RouletteUser, pk=user2_id),
                         roulette=roulette)


class GraphAnalyzer(object):

    def __init__(self, graph, testcase):
        self.testcase = testcase
        # convert list of lists into dict user_id -> dict (user_id -> (weight, penalty_info))
        self.users = {}
        for (user, edge_list) in graph:
            edges = {}
            for user2, weight, penalty_info in edge_list:
                edges[user2.id] = (weight, penalty_info)
            self.users[user.id] = edges

    def assertEdgeExists(self, user1_id, user2_id, expected_weight=None):
        self.testcase.assertIn(user1_id, self.users)
        user1_edges = self.users[user1_id]
        self.testcase.assertIn(user2_id, user1_edges)
        if expected_weight is not None:
            actual_weight, _ = user1_edges[user2_id]
            self.testcase.assertAlmostEqual(expected_weight, actual_weight,
                                            msg="edge between users {0} and {1} should have weight {2}, but got {3}".format(user1_id, user2_id, expected_weight, actual_weight))

    def assertTwoEdgesExist(self, user1_id, user2_id, expected_weight=None):
        self.assertEdgeExists(user1_id, user2_id, expected_weight)
        self.assertEdgeExists(user2_id, user1_id, expected_weight)

    def assertAndRemoveEdge(self, user1_id, user2_id, expected_weight=None):
        self.assertEdgeExists(user1_id, user2_id, expected_weight)
        self.users[user1_id].pop(user2_id)

    def assertAndRemoveTwoEdges(self, user1_id, user2_id, expected_weight=None):
        self.assertAndRemoveEdge(user1_id, user2_id, expected_weight)
        self.assertAndRemoveEdge(user2_id, user1_id, expected_weight)

    def assertNoEdgesLeft(self):
        for user, user_edges in self.users.items():
            self.testcase.assertEqual(
                0, len(user_edges), "for user " + str(user))

    """
    Returns (weight, penalty_info) of the edge between user1 and user2.
    """

    def getEdgeBetween(self, user1_id, user2_id):
        self.assertEdgeExists(user1_id, user2_id)
        return self.users[user1_id][user2_id]


class VoteModelTests(TestCase):

    def test_adding_roulette_adds_default_votes(self):
        create_positive_numbers_users(2)
        Roulette.objects.create(
            vote_deadline=timezone.now(), coffee_deadline=timezone.now())
        all_votes = Vote.objects.all()
        self.assertEqual(2, len(all_votes))

    def test_adding_user_adds_votes(self):
        Roulette.objects.create(
            vote_deadline=timezone.now(), coffee_deadline=timezone.now())
        create_positive_numbers_users(2)
        all_votes = Vote.objects.all()
        self.assertEqual(2, len(all_votes))


class RouletteModelTests(TestCase):

    def test_last_roulette_out_of_two(self):
        expectedLastRoulette = Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now() + timedelta(days=1))
        Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now())
        actualLastRoulette = get_last_roulette()
        self.assertEqual(expectedLastRoulette.pk, actualLastRoulette.pk)

    def test_last_roulette_with_no_finished_roulettes(self):
        Roulette.objects.create(
            vote_deadline=timezone.now(), coffee_deadline=timezone.now())
        self.assertIsNone(get_last_roulette())


class MatchingGraphGenerationTests(TestCase):

    def test_full_graph_for_no_exclusions(self):
        user_count = 10
        users = create_positive_numbers_users(user_count)
        g = GraphAnalyzer(matching_graph(users), self)
        for i in range(1, user_count + 1):
            for j in range(1, user_count + 1):
                if i != j:
                    g.assertAndRemoveEdge(i, j, 0)
        g.assertNoEdgesLeft()

    def test_graph_for_exclusion_groups(self):
        user_count = 5
        users = create_positive_numbers_users(user_count)
        create_groups_modulo_k(user_count, 2, ExclusionGroup)
        g = GraphAnalyzer(matching_graph(users), self)
        g.assertAndRemoveTwoEdges(1, 2, 0)
        g.assertAndRemoveTwoEdges(1, 4, 0)
        g.assertAndRemoveTwoEdges(2, 3, 0)
        g.assertAndRemoveTwoEdges(2, 5, 0)
        g.assertAndRemoveTwoEdges(3, 4, 0)
        g.assertAndRemoveTwoEdges(4, 5, 0)
        g.assertNoEdgesLeft()

    def test_graph_for_penalty_groups(self):
        user_count = 3
        users = create_positive_numbers_users(user_count)
        create_groups_modulo_k(user_count, 2, PenaltyGroup)
        g = GraphAnalyzer(matching_graph(users), self)
        g.assertAndRemoveTwoEdges(1, 2, 0)
        g.assertAndRemoveTwoEdges(1, 3, 2)
        g.assertAndRemoveTwoEdges(2, 3, 0)
        g.assertNoEdgesLeft()

    def test_graph_for_second_roulette_has_first_roulette_exclusions(self):
        user_count = 4
        users = create_positive_numbers_users(user_count)
        firstRoulette = Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now())
        create_match(firstRoulette, users[0].id, users[1].id)
        create_match(firstRoulette, users[2].id, users[3].id)
        g = GraphAnalyzer(matching_graph(users), self)
        # Graph should not contain edges between previously matched users
        g.assertAndRemoveTwoEdges(1, 3)
        g.assertAndRemoveTwoEdges(1, 4)
        g.assertAndRemoveTwoEdges(2, 3)
        g.assertAndRemoveTwoEdges(2, 4)
        g.assertNoEdgesLeft()

    def test_graph_for_third_roulette_has_first_roulette_time_penalties(self):
        user_count = 4
        users = create_positive_numbers_users(user_count)
        firstRoulette = Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now() - timedelta(days=1))
        create_match(firstRoulette, 1, 2)
        create_match(firstRoulette, 3, 4)
        # add 2nd roulette
        Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now())
        # Disable penalties for number of matches, as we're not testing them here.
        PenaltyForNumberOfMatches.objects.create(penalty=0.0)
        # Check that user pairs matched in 1st roulette have penalties in 3rd roulette
        g = GraphAnalyzer(matching_graph(users), self)
        (_, penalty_info) = g.getEdgeBetween(1, 2)
        self.assertEqual(len(penalty_info.recent_matches), 1)
        recent_match = penalty_info.recent_matches[0]
        penalty_after_one_day = 364.0 / 365.0
        self.assertAlmostEqual(recent_match.penalty, penalty_after_one_day)
        self.assertEqual(recent_match.days_ago, 1)
        g.assertAndRemoveTwoEdges(1, 2, penalty_after_one_day)
        g.assertAndRemoveTwoEdges(1, 3, 0)
        g.assertAndRemoveTwoEdges(1, 4, 0)
        g.assertAndRemoveTwoEdges(2, 3, 0)
        g.assertAndRemoveTwoEdges(2, 4, 0)
        g.assertAndRemoveTwoEdges(3, 4, penalty_after_one_day)

    def test_graph_for_fourth_roulette_has_penalties_for_number_of_matches(self):
        user_count = 4
        users = create_positive_numbers_users(user_count)
        firstRoulette = Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now() - timedelta(days=1))
        create_match(firstRoulette, 1, 2)
        create_match(firstRoulette, 3, 4)
        second_roulette = Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now())
        create_match(second_roulette, 1, 2)
        # Add third, empty roulette - because the users cannot get matched in consecutive roulettes, but we want users 1 and 2 to be considered.
        Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now())
        # Disable penalties for recent matches, as we're not testing them here.
        PenaltyForRecentMatch.objects.create(penalty=0.0)
        # Check that user pairs matched in 1st (and 2nd in one case) roulette have penalties in 3rd roulette
        g = GraphAnalyzer(matching_graph(users), self)
        penalty_after_two_matches = 1.0
        penalty_after_one_match = 0.5

        (_, penalty_info) = g.getEdgeBetween(1, 2)
        self.assertEqual(len(penalty_info.recent_matches), 2)
        self.assertEqual(penalty_info.number_matches, 2)
        self.assertAlmostEqual(
            penalty_info.number_matches_penalty, penalty_after_two_matches)
        g.assertAndRemoveTwoEdges(1, 2, penalty_after_two_matches)

        g.assertAndRemoveTwoEdges(1, 3, 0)
        g.assertAndRemoveTwoEdges(1, 4, 0)
        g.assertAndRemoveTwoEdges(2, 3, 0)
        g.assertAndRemoveTwoEdges(2, 4, 0)

        (_, penalty_info) = g.getEdgeBetween(3, 4)
        self.assertEqual(len(penalty_info.recent_matches), 1)
        self.assertEqual(penalty_info.number_matches, 1)
        self.assertAlmostEqual(
            penalty_info.number_matches_penalty, penalty_after_one_match)
        g.assertAndRemoveTwoEdges(3, 4, penalty_after_one_match)

    def test_penalty_info_for_two_penalty_groups(self):
        user_count = 4
        users = create_positive_numbers_users(user_count)
        group1 = PenaltyGroup.objects.create()
        group1.users.add(users[0], users[1], users[2])
        group1.save()
        group2 = PenaltyGroup.objects.create()
        group2.users.add(users[0], users[1])
        group2.save()
        g = GraphAnalyzer(matching_graph(users), self)
        _, penalty_info = g.getEdgeBetween(users[0].id, users[1].id)
        self.assertEqual(penalty_info.penalty_group_count, 2)
        self.assertAlmostEqual(penalty_info.penalty_group_penalty, 4.0)
        self.assertFalse(penalty_info.is_forbidden)
        self.assertAlmostEqual(penalty_info.forbidden_penalty, 0.0)
        self.assertEqual(penalty_info.number_matches, 0)
        self.assertAlmostEqual(penalty_info.number_matches_penalty, 0.0)
        self.assertListEqual(penalty_info.recent_matches, [])

    # TODO test with a roulette with matches, but no matching time


class MatchQualityAnalysisTests(TestCase):
    GREEN_PERCENTILE = 33.3
    YELLOW_PERCENTILE = 66.6

    def get_penalty_info(self, match_qualities: List[MatchQuality], user_a: RouletteUser, user_b: RouletteUser) -> PenaltyInfo:
        for match_quality in match_qualities:
            for user1, user2, penalty_info in zip(match_quality.users_a, match_quality.users_b, match_quality.penalty_infos):
                if (user1.id == user_a.id and user2.id == user_b.id) or (user1.id == user_b.id and user2.id == user_a.id):
                    return penalty_info
        raise ValueError("The penalty info between users {} and {} wasn't found".format(
            user_a.id, user_b.id))

    def assertUndirectedEdgeHasColor(self, match_qualities, user_a, user_b, expected_color):
        edges_found = 0
        for match_quality in match_qualities:
            for user1, user2 in zip(match_quality.users_a, match_quality.users_b):
                if (user1.id == user_a.id and user2.id == user_b.id) or (user1.id == user_b.id and user2.id == user_a.id):
                    self.assertEqual(match_quality.color, expected_color)
                    edges_found += 1
        self.assertEqual(edges_found, 1)

    def test_perfect_matches_are_green(self):
        users = create_positive_numbers_users(4)
        graph = matching_graph(users)
        matches = [set(users[:2]), set(users[2:])]
        match_qualities = get_matches_quality(
            graph, matches, 100.0, self.GREEN_PERCENTILE, self.YELLOW_PERCENTILE)

        self.assertUndirectedEdgeHasColor(
            match_qualities, users[0], users[1], MatchColor.GREEN)
        self.assertUndirectedEdgeHasColor(
            match_qualities, users[2], users[3], MatchColor.GREEN)

    def test_matches_with_red_penalty(self):
        users = create_positive_numbers_users(4)
        penaltyGroup = PenaltyGroup.objects.create()
        penaltyGroup.users.add(users[0], users[1])
        penaltyGroup.save()
        graph = matching_graph(users)
        matches = [set(users[:2]), set(users[2:])]
        match_qualities = get_matches_quality(
            graph, matches, 100.0, self.GREEN_PERCENTILE, self.YELLOW_PERCENTILE)

        # We have 6 undirected edges, 1 of which is with a penalty. 5/6 is above the yellow threshold, so the edge should be marked red.
        self.assertUndirectedEdgeHasColor(
            match_qualities, users[0], users[1], MatchColor.RED)
        self.assertUndirectedEdgeHasColor(
            match_qualities, users[2], users[3], MatchColor.GREEN)

        self.assertEqual(len(match_qualities), 2)
        self.assertEqual(
            match_qualities[0].penalty_infos[0].total_penalty(), PenaltyForPenaltyGroup.objects.get_or_create()[0].penalty)
        self.assertEqual(
            match_qualities[1].penalty_infos[0].total_penalty(), 0)

    def test_matches_with_yellow_penalty(self):
        users = create_positive_numbers_users(4)
        penaltyGroup = PenaltyGroup.objects.create()
        penaltyGroup.users.add(users[0], users[1], users[2])
        penaltyGroup.save()
        graph = matching_graph(users)
        matches = [set(users[:2]), set(users[2:])]
        match_qualities = get_matches_quality(
            graph, matches, 100.0, self.GREEN_PERCENTILE, self.YELLOW_PERCENTILE)

        # We have 6 undirected edges, 3 of which is with a penalty. 3/6 is above the green threshold, but below the yellow - so the edge should be yellow.
        self.assertUndirectedEdgeHasColor(
            match_qualities, users[0], users[1], MatchColor.YELLOW)
        self.assertUndirectedEdgeHasColor(
            match_qualities, users[2], users[3], MatchColor.GREEN)

    def test_empty_match_graph(self):
        graph = matching_graph([])
        matches = []
        match_qualities = get_matches_quality(
            graph, matches, 100.0, self.GREEN_PERCENTILE, self.YELLOW_PERCENTILE)
        self.assertEqual(0, len(match_qualities))

    def test_match_with_exclusion_group_has_proper_penalty_info(self):
        users = create_positive_numbers_users(4)
        exclusionGroup = ExclusionGroup.objects.create()
        exclusionGroup.users.add(users[0], users[1], users[2])
        exclusionGroup.save()
        graph = matching_graph(users)
        matches = [set(users[:2]), set(users[2:])]
        match_qualities = get_matches_quality(
            graph, matches, 100.0, self.GREEN_PERCENTILE, self.YELLOW_PERCENTILE)
        penalty_info = self.get_penalty_info(
            match_qualities, users[0], users[1])
        self.assertTrue(penalty_info.is_forbidden)
        self.assertEqual(penalty_info.forbidden_penalty, 100.0)
        self.assertAlmostEqual(penalty_info.total_penalty(), 100.0)

    def test_four_users_in_match_group(self):
        users = create_positive_numbers_users(4)
        graph = matching_graph(users)
        matches = [set(users)]
        match_qualities = get_matches_quality(
            graph, matches, 100.0, self.GREEN_PERCENTILE, self.YELLOW_PERCENTILE)
        self.assertEqual(len(match_qualities), 1)
        match_quality = match_qualities[0]
        self.assertEqual(6, len(match_quality.users_a))
        self.assertEqual(6, len(match_quality.users_b))
        self.assertCountEqual(match_quality.users_in_match_group(), users)


class MatchingAlgorithmsTest(TestCase):
    pass


class HarryPotterMatchingTest(MatchingAlgorithmsTest):
    # Dump the fixture by:
    # python manage.py dumpdata matcher --exclude matcher.vote --indent 2 > matcher/fixtures/<name>.json
    # Then, consider de-personalizing the data.
    # matcher.vote has been excluded because of unique constraint violation while importing the fixture (a bug?)
    fixtures = ['harry_potter.json']
    today = datetime(2021, 3, 3, 18)

    def test_reads_all_users_in_fixture(self):
        user_count = RouletteUser.objects.count()
        self.assertEquals(14, user_count)
