from django.db import transaction
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.utils import timezone
from django.urls import reverse
from .algorithms import generate_matches_montecarlo, merge_matches
from .models import Match, Roulette, RouletteUser, PenaltyForGroupingWithForbiddenUser, matching_graph
import re



def current_roulette(request):
    roulettes = Roulette.objects.filter(coffee_deadline__gte=timezone.now()).all()
    context = {'roulettes': roulettes}
    return render(request, 'matcher/current_roulette.html', context)

def roulette(request, roulette_id):
    r = get_object_or_404(Roulette, pk=roulette_id)
    context = {'roulette': r, 'pretty_state': r.getPrettyState, 'votes': r.vote_set.order_by('user__name'),
              'matches': merge_matches(r.match_set.all()) }
    return render(request, 'matcher/roulette.html', context)

def run_roulette(request, roulette_id):
    r = get_object_or_404(Roulette, pk=roulette_id)
    if not r.canAdminGenerateMatches():
       return render(request, 'matcher/cant_generate_matches.html', {'roulette': r})
    users = r.participatingUsers()
    graph = matching_graph(users)
    penalty_for_grouping_with_forbidden_user = PenaltyForGroupingWithForbiddenUser.objects.get_or_create()[0].penalty
    matches = generate_matches_montecarlo(graph, penalty_for_grouping_with_forbidden_user)
    context = {'matches': matches, 'roulette': r}
    return render(request, 'matcher/matcher.html', context)

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
                    Match.objects.create(user_a = get_object_or_404(RouletteUser, pk=user_a),
                                         user_b = get_object_or_404(RouletteUser, pk=user_b),
                                         roulette = r)
        transaction.commit()
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
        