<template>
  <section
    v-if="invitations.length || otherHouseholds.length"
    data-test="household-memberships"
  >
    <BaseDialog
      v-model="leaveDialog"
      :title="$t('household.leave-household')"
      :icon="$globals.icons.alertCircle"
      color="error"
      can-confirm
      @confirm="confirmLeave"
    >
      <v-card-text>
        {{ $t('household.leave-household-confirm', { household: leaveTarget?.householdName ?? '' }) }}
      </v-card-text>
    </BaseDialog>

    <v-divider class="my-7" />

    <div v-if="invitations.length">
      <h3 class="text-h6 mb-2">
        {{ $t('household.pending-invitations') }}
      </h3>
      <v-card
        v-for="invitation in invitations"
        :key="invitation.id"
        class="mb-2"
        variant="outlined"
      >
        <v-card-text class="d-flex align-center flex-wrap ga-2">
          <div class="flex-grow-1">
            <div class="font-weight-medium">
              {{ $t('household.invited-to-household', { household: invitation.householdName }) }}
            </div>
            <div
              v-if="invitation.invitedByName"
              class="text-caption text-medium-emphasis"
            >
              {{ $t('household.invited-by', { name: invitation.invitedByName }) }}
            </div>
          </div>
          <v-btn
            data-test="decline-invitation"
            variant="text"
            @click="answer(invitation, false)"
          >
            {{ $t('household.decline-invitation') }}
          </v-btn>
          <v-btn
            data-test="accept-invitation"
            color="primary"
            @click="answer(invitation, true)"
          >
            {{ $t('household.accept-invitation') }}
          </v-btn>
        </v-card-text>
      </v-card>
    </div>

    <div
      v-if="otherHouseholds.length"
      :class="{ 'mt-6': invitations.length }"
    >
      <h3 class="text-h6 mb-2">
        {{ $t('household.your-households') }}
      </h3>
      <v-list>
        <v-list-item
          v-for="household in households"
          :key="household.householdId"
          :title="household.householdName"
          :subtitle="household.isPrimary ? $t('household.primary-household') : undefined"
        >
          <template #append>
            <v-btn
              v-if="!household.isPrimary"
              data-test="leave-household"
              :data-household="household.householdId"
              variant="text"
              color="error"
              @click="openLeave(household)"
            >
              {{ $t('household.leave-household') }}
            </v-btn>
          </template>
        </v-list-item>
      </v-list>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useHouseholdInvitations } from "~/composables/use-household-invitations";
import { alert } from "~/composables/use-toast";
import type { ReadHouseholdMemberInvitation } from "~/lib/api/types/household";
import type { UserHouseholdMembershipOut } from "~/lib/api/types/user";

/**
 * Invitations to join other households, and the households the user can leave. Shown on the profile page,
 * and only when there's something to show: a user with a single household and no invitations sees nothing.
 */
const i18n = useI18n();
const { user } = useMealieAuth();
const { invitations, refresh, accept, decline, leave } = useHouseholdInvitations();

const households = computed(() => user.value?.households ?? []);
const otherHouseholds = computed(() => households.value.filter(household => !household.isPrimary));

async function answer(invitation: ReadHouseholdMemberInvitation, accepted: boolean) {
  const ok = accepted ? await accept(invitation.id) : await decline(invitation.id);

  if (!ok) {
    alert.error(i18n.t("events.something-went-wrong"));
  }
  else if (accepted) {
    alert.success(i18n.t("household.invitation-accepted", { household: invitation.householdName }));
  }
  else {
    alert.success(i18n.t("household.invitation-declined"));
  }
}

const leaveDialog = ref(false);
const leaveTarget = ref<UserHouseholdMembershipOut | null>(null);

function openLeave(household: UserHouseholdMembershipOut) {
  leaveTarget.value = household;
  leaveDialog.value = true;
}

async function confirmLeave() {
  const household = leaveTarget.value;
  if (!household) {
    return;
  }

  if (await leave(household.householdId)) {
    alert.success(i18n.t("household.left-household", { household: household.householdName }));
  }
  else {
    alert.error(i18n.t("events.something-went-wrong"));
  }
  leaveTarget.value = null;
}

onMounted(refresh);
</script>
