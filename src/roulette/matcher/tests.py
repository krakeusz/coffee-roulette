from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.test import TestCase
from django.utils import timezone

from .models import Roulette, Vote, Match, RouletteUser, ExclusionGroup, PenaltyGroup, PenaltyForPenaltyGroup, PenaltyForNumberOfMatches, get_last_roulette, matching_graph, MatchColor
from .algorithms import get_matches_quality


def create_natural_number_users(n_users):
    for i in range(1, n_users+1):
        RouletteUser.objects.create(name=str(i), email=str(i)+"@example.com")
    return RouletteUser.objects.all()


def create_groups_modulo_k(n_users, k_groups, group_model):
    """
    Creates k_groups exclusion or penalty groups of 'natural number users', containing users in the same modulo group.
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
        # convert list of lists into dict user -> dict (user -> weight)
        self.users = {}
        for (user, edge_list) in graph:
            edges = {}
            for user2, weight, _ in edge_list:
                edges[user2.id] = weight
            self.users[user.id] = edges

    def assertEdgeExists(self, user1_id, user2_id, expected_weight=None):
        self.testcase.assertIn(user1_id, self.users)
        user1_edges = self.users[user1_id]
        self.testcase.assertIn(user2_id, user1_edges)
        if expected_weight is not None:
            self.testcase.assertAlmostEqual(expected_weight, user1_edges[user2_id],
                                            msg="edge between users {0} and {1} should have weight {2}, but got {3}".format(user1_id, user2_id, expected_weight, user1_edges[user2_id]))

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


class VoteModelTests(TestCase):

    def test_adding_roulette_adds_default_votes(self):
        create_natural_number_users(2)
        Roulette.objects.create(
            vote_deadline=timezone.now(), coffee_deadline=timezone.now())
        all_votes = Vote.objects.all()
        self.assertEqual(2, len(all_votes))

    def test_adding_user_adds_votes(self):
        Roulette.objects.create(
            vote_deadline=timezone.now(), coffee_deadline=timezone.now())
        create_natural_number_users(2)
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
        users = create_natural_number_users(user_count)
        g = GraphAnalyzer(matching_graph(users), self)
        for i in range(1, user_count + 1):
            for j in range(1, user_count + 1):
                if i != j:
                    g.assertAndRemoveEdge(i, j, 0)
        g.assertNoEdgesLeft()

    def test_graph_for_exclusion_groups(self):
        user_count = 5
        users = create_natural_number_users(user_count)
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
        users = create_natural_number_users(user_count)
        create_groups_modulo_k(user_count, 2, PenaltyGroup)
        g = GraphAnalyzer(matching_graph(users), self)
        g.assertAndRemoveTwoEdges(1, 2, 0)
        g.assertAndRemoveTwoEdges(1, 3, 2)
        g.assertAndRemoveTwoEdges(2, 3, 0)
        g.assertNoEdgesLeft()

    def test_graph_for_second_roulette_has_first_roulette_exclusions(self):
        user_count = 4
        users = create_natural_number_users(user_count)
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

    def test_graph_for_third_roulette_has_first_roulette_penalties(self):
        user_count = 4
        users = create_natural_number_users(user_count)
        firstRoulette = Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now() - timedelta(days=1))
        create_match(firstRoulette, users[0].id, users[1].id)
        create_match(firstRoulette, users[2].id, users[3].id)
        # add 2nd roulette
        Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now())
        # Disable penalties for number of matches, as we're not testing it here.
        PenaltyForNumberOfMatches.objects.create(penalty=0.0)
        # Check that user pairs matched in 1st roulette have penalties in 3rd roulette
        g = GraphAnalyzer(matching_graph(users), self)
        penalty_after_one_day = 364.0 / 365.0
        g.assertAndRemoveTwoEdges(1, 2, penalty_after_one_day)
        g.assertAndRemoveTwoEdges(1, 3, 0)
        g.assertAndRemoveTwoEdges(1, 4, 0)
        g.assertAndRemoveTwoEdges(2, 3, 0)
        g.assertAndRemoveTwoEdges(2, 4, 0)
        g.assertAndRemoveTwoEdges(3, 4, penalty_after_one_day)

        # TODO test with a roulette with matches, but no matching time


class MatchQualityAnalysisTests(TestCase):
    GREEN_PERCENTILE = 33.3
    YELLOW_PERCENTILE = 66.6

    def test_perfect_matches_are_green(self):
        users = create_natural_number_users(4)
        Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now())
        graph = matching_graph(users)
        matches = [set(users[:2]), set(users[2:])]
        match_qualities = get_matches_quality(
            graph, matches, 100.0, self.GREEN_PERCENTILE, self.YELLOW_PERCENTILE)

        self.assertEqual(len(match_qualities), 2)
        self.assertEqual(match_qualities[0].users_a, [users[0]])
        self.assertEqual(match_qualities[0].users_b, [users[1]])
        self.assertEqual(match_qualities[0].color, MatchColor.GREEN)
        self.assertEqual(
            match_qualities[0].penalty_infos[0].total_penalty(), 0)

        self.assertEqual(match_qualities[1].users_a, [users[2]])
        self.assertEqual(match_qualities[1].users_b, [users[3]])
        self.assertEqual(match_qualities[1].color, MatchColor.GREEN)
        self.assertEqual(
            match_qualities[1].penalty_infos[0].total_penalty(), 0)

    def test_matches_with_red_penalty(self):
        users = create_natural_number_users(4)
        penaltyGroup = PenaltyGroup.objects.create()
        penaltyGroup.users.add(users[0], users[1])
        penaltyGroup.save()
        Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now())
        graph = matching_graph(users)
        matches = [set(users[:2]), set(users[2:])]
        match_qualities = get_matches_quality(
            graph, matches, 100.0, self.GREEN_PERCENTILE, self.YELLOW_PERCENTILE)

        self.assertEqual(len(match_qualities), 2)
        self.assertEqual(match_qualities[0].users_a, [users[0]])
        self.assertEqual(match_qualities[0].users_b, [users[1]])
        # We have 6 undirected edges, 1 of which is with a penalty. 5/6 is above the yellow threshold, so the edge should be marked red.
        self.assertEqual(match_qualities[0].color, MatchColor.RED)
        self.assertEqual(
            match_qualities[0].penalty_infos[0].total_penalty(), PenaltyForPenaltyGroup.objects.get_or_create()[0].penalty)

        self.assertEqual(match_qualities[1].users_a, [users[2]])
        self.assertEqual(match_qualities[1].users_b, [users[3]])
        self.assertEqual(match_qualities[1].color, MatchColor.GREEN)
        self.assertEqual(
            match_qualities[1].penalty_infos[0].total_penalty(), 0)

    def test_matches_with_yellow_penalty(self):
        users = create_natural_number_users(4)
        penaltyGroup = PenaltyGroup.objects.create()
        penaltyGroup.users.add(users[0], users[1], users[2])
        penaltyGroup.save()
        Roulette.objects.create(vote_deadline=timezone.now(
        ), coffee_deadline=timezone.now(), matchings_found_on=timezone.now())
        graph = matching_graph(users)
        matches = [set(users[:2]), set(users[2:])]
        match_qualities = get_matches_quality(
            graph, matches, 100.0, self.GREEN_PERCENTILE, self.YELLOW_PERCENTILE)

        self.assertEqual(len(match_qualities), 2)
        self.assertEqual(match_qualities[0].users_a, [users[0]])
        self.assertEqual(match_qualities[0].users_b, [users[1]])
        # We have 6 undirected edges, 3 of which is with a penalty. 3/6 is above the green threshold, but below the yellow - so the edge should be yellow.
        self.assertEqual(match_qualities[0].color, MatchColor.YELLOW)
        self.assertEqual(
            match_qualities[0].penalty_infos[0].total_penalty(), PenaltyForPenaltyGroup.objects.get_or_create()[0].penalty)

        self.assertEqual(match_qualities[1].users_a, [users[2]])
        self.assertEqual(match_qualities[1].users_b, [users[3]])
        self.assertEqual(match_qualities[1].color, MatchColor.GREEN)
        self.assertEqual(
            match_qualities[1].penalty_infos[0].total_penalty(), 0)
