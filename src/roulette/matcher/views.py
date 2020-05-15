from django.db import transaction
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_POST
from .algorithms import generate_matches_montecarlo, merge_matches
from .models import Match, Roulette, RouletteUser, PenaltyForGroupingWithForbiddenUser, matching_graph
from .signals import post_matching
import re


def insert_roulette_data_columns(roulettes):
    for r in roulettes:
        votes = r.vote_set.order_by('user__name')
        r.votes_yes = len(votes.filter(choice='Y'))
        r.votes_no = len(votes.filter(choice='N'))
        r.votes_unknown = len(votes.filter(choice='0'))
        r.total_users = r.votes_yes + r.votes_no + r.votes_unknown


def roulette_list_active(request):
    roulettes = Roulette.objects.filter(
        coffee_deadline__gte=timezone.now()).order_by("-id").all()
    insert_roulette_data_columns(roulettes)
    return render(request, 'matcher/roulette_list_active.html', {'roulettes': roulettes})


def roulette_list_archive(request):
    roulettes = Roulette.objects.filter(
        coffee_deadline__lt=timezone.now()).order_by("-id").all()
    insert_roulette_data_columns(roulettes)
    return render(request, 'matcher/roulette_list_archive.html', {'roulettes': roulettes})


def roulette_list_all(request):
    roulettes = Roulette.objects.order_by("-id").all()
    insert_roulette_data_columns(roulettes)
    return render(request, 'matcher/roulette_list_all.html', {'roulettes': roulettes})


def roulette(request, roulette_id):
    r = get_object_or_404(Roulette, pk=roulette_id)
    votes = r.vote_set.order_by('user__name')
    context = {'roulette': r, 'pretty_state': r.getPrettyState, 'votes_yes': votes.filter(choice='Y'),
               'votes_no': votes.filter(choice='N'), 'votes_unknown': votes.filter(choice='0'),
               'matches': merge_matches(r.match_set.all())}
    return render(request, 'matcher/roulette.html', context)


def run_roulette(request, roulette_id):
    r = get_object_or_404(Roulette, pk=roulette_id)
    if not r.canAdminGenerateMatches():
        return render(request, 'matcher/cant_generate_matches.html', {'roulette': r})
    users = r.participatingUsers()
    graph = matching_graph(users)
    penalty_for_grouping_with_forbidden_user = PenaltyForGroupingWithForbiddenUser.objects.get_or_create()[
        0].penalty
    matches = generate_matches_montecarlo(
        graph, penalty_for_grouping_with_forbidden_user)
    context = {'matches': matches, 'roulette': r}
    # TODO refactor this to use session data instead
    return render(request, 'matcher/matcher.html', context)


@require_POST
def submit_roulette(request, roulette_id):
    autocommit = transaction.get_autocommit()
    transaction.set_autocommit(False)
    exception = None
    try:
        r = Roulette.objects.select_for_update().get(id=roulette_id)
        if r.matchings_found_on is not None:
            raise Exception("Someone else has already saved the results")
        r.matchings_found_on = timezone.now()
        r.save()
        groups = {}
        user_ids_affected = set()
        for key, value in request.POST.items():
            pattern = r'user(\d+)$'
            match = re.match(pattern, key)
            if match:
                group_id = value
                user_id = int(match.group(1))
                group = groups.get(group_id, [])
                group.append(user_id)
                if user_id in user_ids_affected:
                    raise Exception("A user can't have more than 1 match")
                user_ids_affected.add(user_id)
                groups[group_id] = group
        for group in groups.values():
            for user_a in group:
                for user_b in group:
                    if user_a >= user_b:
                        continue
                    Match.objects.create(user_a=get_object_or_404(RouletteUser, pk=user_a),
                                         user_b=get_object_or_404(
                                             RouletteUser, pk=user_b),
                                         roulette=r)
        transaction.commit()
        post_matching.send(sender=Roulette.__class__,
                           instance=r, groups=groups)
    except (KeyError, Roulette.DoesNotExist):
        exception = Http404()
        transaction.rollback()
    except Exception as e:
        exception = e
        transaction.rollback()
    transaction.set_autocommit(autocommit)
    if exception is None:
        return HttpResponseRedirect(reverse('matcher:roulette', args=(r.id,)))
    else:
        raise exception
