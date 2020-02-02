from django.contrib import admin
from .models import *

class VoteInline(admin.TabularInline):
    model = Vote
    extra = 0
    can_delete = False
    fields = ("user", "choice")
    readonly_fields=("user",)

    def has_add_permission(self, request, obj):
        return False
    
    def has_change_permission(self, request, obj):
        if obj is None:
            return True # Generally, editing is allowed.
        if not isinstance(obj, Roulette):
            return False # Disallow editing from anything other than Roulette view
        # Allow editing votes if the model logic allows to.
        return obj.canAdminChangeVotes()

class RouletteAdmin(admin.ModelAdmin):
    exclude=("matchings_found_on",)
    readonly_fields=("matchings_found_on", )
    inlines = [VoteInline]

admin.site.register(Roulette, RouletteAdmin)
admin.site.register(RouletteUser)
admin.site.register(ExclusionGroup)
admin.site.register(PenaltyGroup)
admin.site.register(PenaltyForRecentMatch)
admin.site.register(PenaltyForNumberOfMatches)
admin.site.register(PenaltyForPenaltyGroup)
admin.site.register(PenaltyForGroupingWithForbiddenUser)
