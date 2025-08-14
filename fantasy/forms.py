from __future__ import annotations

from decimal import Decimal
from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Count, F

from league.models import Player
from .models import FantasyLeague, FantasyTeam, FantasyPlayer
from .utils import get_current_week, is_before_deadline


class FantasyTeamCreateForm(forms.ModelForm):
    class Meta:
        model = FantasyTeam
        fields = ["name"]


class AddFantasyPlayerForm(forms.Form):
    player_id = forms.IntegerField(min_value=1)

    def __init__(self, *args, fantasy_team: FantasyTeam, **kwargs):
        super().__init__(*args, **kwargs)
        self.fantasy_team = fantasy_team

    def clean(self):
        cleaned = super().clean()
        league: FantasyLeague = self.fantasy_team.fantasy_league
        player_id = cleaned.get("player_id")
        if not player_id:
            return cleaned

        try:
            player = Player.objects.get(id=player_id)
        except Player.DoesNotExist:
            raise forms.ValidationError("Player not found")

        # Budget check
        if player.price > self.fantasy_team.balance:
            raise forms.ValidationError("Insufficient balance for this transfer")

        # Max team size
        active_count = self.fantasy_team.fantasy_players.filter(active_to__isnull=True).count()
        if active_count >= league.max_team_size:
            raise forms.ValidationError("Team is at maximum size")

        # Per-real-team constraint
        from league.models import PlayerSeasonParticipation
        current_season_participation = PlayerSeasonParticipation.objects.filter(player=player, is_active=True).first()
        team_id = current_season_participation.team_id if current_season_participation else None
        if team_id:
            real_team_count = self.fantasy_team.fantasy_players.filter(
                active_to__isnull=True, player__playerseasonparticipation__team_id=team_id, player__playerseasonparticipation__is_active=True
            ).count()
            if real_team_count >= league.max_per_real_team:
                raise forms.ValidationError("Exceeded allowed number of players from this real team")

        cleaned["player"] = player
        # Enforce weekly transfer limit
        week = get_current_week(league)
        if week:
            from .models import FantasyTransfer
            transfers_this_week = FantasyTransfer.objects.filter(
                fantasy_team=self.fantasy_team,
                fantasy_match_week=week,
                action__in=[FantasyTransfer.Action.ADD, FantasyTransfer.Action.SWAP],
            ).count()
            if transfers_this_week >= league.transfer_limit:
                raise forms.ValidationError("Weekly transfer limit reached")
            if not is_before_deadline(week):
                raise forms.ValidationError("Deadline passed for this week")
        cleaned["week"] = week
        return cleaned

    def save(self) -> FantasyPlayer:
        player: Player = self.cleaned_data["player"]
        week = self.cleaned_data.get("week")
        fp = FantasyPlayer.objects.create(
            fantasy_team=self.fantasy_team,
            player=player,
            price_at_purchase=player.price,
            active_from=self.fantasy_team.fantasy_league.start_date,
        )
        # Deduct balance
        self.fantasy_team.balance = (self.fantasy_team.balance or Decimal("0")) - player.price
        self.fantasy_team.save(update_fields=["balance", "updated_at"])
        # Log transfer
        if week:
            from .models import FantasyTransfer
            FantasyTransfer.objects.create(
                fantasy_team=self.fantasy_team,
                fantasy_match_week=week,
                action=FantasyTransfer.Action.ADD,
                player_in=player,
                cost=player.price,
            )
        return fp


class RemoveFantasyPlayerForm(forms.Form):
    fantasy_player_id = forms.IntegerField(min_value=1)

    def __init__(self, *args, fantasy_team: FantasyTeam, **kwargs):
        super().__init__(*args, **kwargs)
        self.fantasy_team = fantasy_team

    def clean(self):
        cleaned = super().clean()
        fp_id = cleaned.get("fantasy_player_id")
        if not fp_id:
            return cleaned
        try:
            fp = FantasyPlayer.objects.get(id=fp_id, fantasy_team=self.fantasy_team, active_to__isnull=True)
        except FantasyPlayer.DoesNotExist:
            raise forms.ValidationError("Fantasy player not found or already inactive")
        cleaned["fp"] = fp
        return cleaned

    def save(self) -> FantasyPlayer:
        fp: FantasyPlayer = self.cleaned_data["fp"]
        team = self.fantasy_team
        league: FantasyLeague = team.fantasy_league
        # Week and deadline check
        week = get_current_week(league)
        if week and not is_before_deadline(week):
            raise forms.ValidationError("Deadline passed for this week")

        # Refund based on league policy
        refund = fp.price_at_purchase if team.fantasy_league.sell_price_policy == FantasyLeague.SellPricePolicy.PURCHASE else fp.player.price
        team.balance = (team.balance or Decimal("0")) + refund
        team.save(update_fields=["balance", "updated_at"])
        fp.active_to = team.fantasy_league.end_date
        fp.save(update_fields=["active_to"])

        # Log transfer out if week exists
        if week:
            from .models import FantasyTransfer
            FantasyTransfer.objects.create(
                fantasy_team=team,
                fantasy_match_week=week,
                action=FantasyTransfer.Action.REMOVE,
                player_out=fp.player,
                cost=0,
            )
        return fp


class SetCaptainForm(forms.Form):
    fantasy_player_id = forms.IntegerField(min_value=1)

    def __init__(self, *args, fantasy_team: FantasyTeam, **kwargs):
        super().__init__(*args, **kwargs)
        self.fantasy_team = fantasy_team

    def clean(self):
        cleaned = super().clean()
        fp_id = cleaned.get("fantasy_player_id")
        if not fp_id:
            return cleaned
        try:
            fp = FantasyPlayer.objects.get(id=fp_id, fantasy_team=self.fantasy_team, active_to__isnull=True)
        except FantasyPlayer.DoesNotExist:
            raise forms.ValidationError("Fantasy player not found or inactive")
        league: FantasyLeague = self.fantasy_team.fantasy_league
        week = get_current_week(league)
        if week and not is_before_deadline(week):
            raise forms.ValidationError("Deadline passed for this week")
        cleaned["fp"] = fp
        return cleaned

    def save(self) -> FantasyPlayer:
        fp: FantasyPlayer = self.cleaned_data["fp"]
        # Unset previous captain
        FantasyPlayer.objects.filter(fantasy_team=self.fantasy_team, active_to__isnull=True, is_captain=True).update(is_captain=False)
        fp.is_captain = True
        fp.save(update_fields=["is_captain"])
        return fp


class SetViceCaptainForm(forms.Form):
    fantasy_player_id = forms.IntegerField(min_value=1)

    def __init__(self, *args, fantasy_team: FantasyTeam, **kwargs):
        super().__init__(*args, **kwargs)
        self.fantasy_team = fantasy_team

    def clean(self):
        cleaned = super().clean()
        fp_id = cleaned.get("fantasy_player_id")
        if not fp_id:
            return cleaned
        try:
            fp = FantasyPlayer.objects.get(id=fp_id, fantasy_team=self.fantasy_team, active_to__isnull=True)
        except FantasyPlayer.DoesNotExist:
            raise forms.ValidationError("Fantasy player not found or inactive")
        league: FantasyLeague = self.fantasy_team.fantasy_league
        week = get_current_week(league)
        if week and not is_before_deadline(week):
            raise forms.ValidationError("Deadline passed for this week")
        cleaned["fp"] = fp
        return cleaned

    def save(self) -> FantasyPlayer:
        fp: FantasyPlayer = self.cleaned_data["fp"]
        # Unset previous vice captain
        FantasyPlayer.objects.filter(fantasy_team=self.fantasy_team, active_to__isnull=True, is_vice_captain=True).update(is_vice_captain=False)
        fp.is_vice_captain = True
        fp.save(update_fields=["is_vice_captain"])
        return fp


