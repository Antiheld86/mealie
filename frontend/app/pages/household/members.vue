<template>
  <v-container>
    <BasePageTitle divider>
      <template #header>
        <v-img
          width="100%"
          max-height="125"
          max-width="125"
          src="/svgs/manage-members.svg"
        />
      </template>
      <template #title>
        {{ $t('group.manage-members') }}
      </template>
      <i18n-t keypath="group.manage-members-description">
        <template #manage>
          <b>{{ $t('group.manage') }}</b>
        </template>
        <template #organize>
          <b>{{ $t('settings.organize') }}</b>
        </template>
        <template #invite>
          <b>{{ $t('group.invite') }}</b>
        </template>
      </i18n-t>
      <v-container class="mt-1 px-0">
        <nuxt-link
          class="text-center text-primary"
          :to="`/user/profile/edit`"
        > {{ $t('group.looking-to-update-your-profile') }}
        </nuxt-link>
      </v-container>
    </BasePageTitle>

    <v-row
      align="center"
      class="mb-2"
    >
      <v-col
        cols="12"
        sm="6"
        md="4"
      >
        <HouseholdContextSelect />
      </v-col>
      <v-spacer />
      <v-col
        v-if="canManage"
        cols="12"
        sm="auto"
      >
        <v-btn
          color="primary"
          :prepend-icon="$globals.icons.createAlt"
          @click="inviteDialog = true"
        >
          {{ $t('household.invite-member') }}
        </v-btn>
      </v-col>
    </v-row>

    <BaseDialog
      v-model="inviteDialog"
      :title="$t('household.invite-member')"
      :icon="$globals.icons.user"
      can-submit
      :submit-disabled="!inviteEmail.trim()"
      @submit="submitInvite"
    >
      <v-card-text>
        <p class="mb-4">
          {{ $t('household.invite-member-description') }}
        </p>
        <v-text-field
          v-model="inviteEmail"
          type="email"
          autofocus
          :label="$t('household.invite-member-email')"
          @keyup.enter="submitInvite"
        />
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="removeDialog"
      :title="$t('household.remove-member')"
      :icon="$globals.icons.alertCircle"
      color="error"
      can-confirm
      @confirm="confirmRemove"
    >
      <v-card-text>
        {{ $t('household.remove-member-confirm', { name: removeTarget?.fullName || removeTarget?.username || '' }) }}
      </v-card-text>
    </BaseDialog>

    <v-data-table
      :headers="headers"
      :items="members || []"
      item-key="id"
      class="elevation-0"
      :items-per-page="-1"
      hide-default-footer
      disable-pagination
    >
      <template #[`header.manage`]="{ column }">
        {{ column.title }}
        <v-tooltip location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" size="small" class="ms-1">
              {{ $globals.icons.informationOutline }}
            </v-icon>
          </template>
          <span>{{ $t('user.user-can-manage-group-hint') }}</span>
        </v-tooltip>
      </template>
      <template #[`header.organize`]="{ column }">
        {{ column.title }}
        <v-tooltip location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" size="small" class="ms-1">
              {{ $globals.icons.informationOutline }}
            </v-icon>
          </template>
          <span>{{ $t('user.user-can-organize-group-data-hint') }}</span>
        </v-tooltip>
      </template>
      <template #[`header.invite`]="{ column }">
        {{ column.title }}
        <v-tooltip location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" size="small" class="ms-1">
              {{ $globals.icons.informationOutline }}
            </v-icon>
          </template>
          <span>{{ $t('user.user-can-invite-other-to-group-hint') }}</span>
        </v-tooltip>
      </template>
      <template #[`header.manageHousehold`]="{ column }">
        {{ column.title }}
        <v-tooltip location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-icon v-bind="tooltipProps" size="small" class="ms-1">
              {{ $globals.icons.informationOutline }}
            </v-icon>
          </template>
          <span>{{ $t('user.user-can-manage-household-hint') }}</span>
        </v-tooltip>
      </template>
      <template #[`item.avatar`]="{ item }">
        <UserAvatar
          v-if="item"
          :tooltip="false"
          :user-id="item.id"
        />
      </template>
      <template #[`item.household`]="{ item }">
        <v-chip
          v-if="item"
          size="small"
          label
          :color="isPrimaryMember(item) ? 'primary' : undefined"
        >
          {{ isPrimaryMember(item) ? $t('household.primary-household') : $t('household.additional-member') }}
        </v-chip>
      </template>
      <template #[`item.actions`]="{ item }">
        <v-btn
          v-if="item && canManage && !isPrimaryMember(item)"
          icon
          variant="text"
          size="small"
          color="error"
          :title="$t('household.remove-member')"
          @click="openRemove(item)"
        >
          <v-icon>{{ $globals.icons.delete }}</v-icon>
        </v-btn>
      </template>
      <template #[`item.admin`]="{ item }">
        {{ item && item.admin ? $t('user.admin') : $t('user.user') }}
      </template>
      <template #[`item.manageHousehold`]="{ item }">
        <div
          v-if="item"
          class="d-flex justify-center"
        >
          <v-checkbox
            :model-value="canManageHousehold(item)"
            :disabled="item.id === sessionUser?.id || item.admin"
            color="primary"
            class=""
            style="max-width: 30px"
            hide-details
            @update:model-value="setManageHousehold(item, !!$event)"
          />
        </div>
      </template>
      <template #[`item.manage`]="{ item }">
        <div
          v-if="item"
          class="d-flex justify-center"
        >
          <v-checkbox
            v-model="item.canManage"
            :disabled="item.id === sessionUser?.id || item.admin || !isPrimaryMember(item)"
            class=""
            style="max-width: 30px"
            hide-details
            color="primary"
            @change="setGroupPermissions(item)"
          />
        </div>
      </template>
      <template #[`item.organize`]="{ item }">
        <div
          v-if="item"
          class="d-flex justify-center"
        >
          <v-checkbox
            v-model="item.canOrganize"
            :disabled="item.id === sessionUser?.id || item.admin || !isPrimaryMember(item)"
            class=""
            style="max-width: 30px"
            hide-details
            color="primary"
            @change="setGroupPermissions(item)"
          />
        </div>
      </template>
      <template #[`item.invite`]="{ item }">
        <div
          v-if="item"
          class="d-flex justify-center"
        >
          <v-checkbox
            v-model="item.canInvite"
            :disabled="item.id === sessionUser?.id || item.admin || !isPrimaryMember(item)"
            class=""
            style="max-width: 30px"
            hide-details
            color="primary"
            @change="setGroupPermissions(item)"
          />
        </div>
      </template>
    </v-data-table>

    <template v-if="canManage">
      <h3 class="text-h6 mt-8 mb-2">
        {{ $t('household.pending-invitations') }}
      </h3>
      <v-list v-if="invitations.length">
        <v-list-item
          v-for="invitation in invitations"
          :key="invitation.id"
          :title="invitation.userName"
          :subtitle="invitation.invitedByName ? $t('household.invited-by', { name: invitation.invitedByName }) : undefined"
        >
          <template #append>
            <v-btn
              variant="text"
              color="error"
              @click="revoke(invitation.id)"
            >
              {{ $t('household.revoke-invitation') }}
            </v-btn>
          </template>
        </v-list-item>
      </v-list>
      <p
        v-else
        class="text-medium-emphasis"
      >
        {{ $t('household.no-pending-invitations') }}
      </p>
    </template>
  </v-container>
</template>

<script setup lang="ts">
import HouseholdContextSelect from "~/components/Domain/Household/HouseholdContextSelect.vue";
import UserAvatar from "~/components/Domain/User/UserAvatar.vue";
import { useHouseholdContext } from "~/composables/use-household-context";
import { useHouseholdMembers } from "~/composables/use-household-members";
import { alert } from "~/composables/use-toast";
import type { UserOut } from "~/lib/api/types/user";

definePageMeta({
  middleware: ["auth"],
});

const i18n = useI18n();
const auth = useMealieAuth();
const sessionUser = computed(() => auth.user.value);

useSeoMeta({
  title: i18n.t("profile.members"),
});

const { canManage } = useHouseholdContext();
const {
  members,
  invitations,
  refresh,
  isPrimaryMember,
  canManageHousehold,
  invite,
  revoke,
  remove,
  setPermissions,
} = useHouseholdMembers();

const headers = [
  { title: "", value: "avatar", sortable: false, align: "center" },
  { title: i18n.t("user.username"), value: "username" },
  { title: i18n.t("user.full-name"), value: "fullName" },
  { title: i18n.t("household.household"), value: "household", sortable: false },
  { title: i18n.t("user.admin"), value: "admin" },
  { title: i18n.t("group.manage"), value: "manage", sortable: false, align: "center" },
  { title: i18n.t("settings.organize"), value: "organize", sortable: false, align: "center" },
  { title: i18n.t("group.invite"), value: "invite", sortable: false, align: "center" },
  { title: i18n.t("group.manage-household"), value: "manageHousehold", sortable: false, align: "center" },
  { title: "", value: "actions", sortable: false, align: "end" },
] as const;

// the group-level checkboxes edit the member in place; the household flag is read from the membership
function setGroupPermissions(user: UserOut) {
  return setPermissions(user, canManageHousehold(user));
}

async function setManageHousehold(user: UserOut, value: boolean) {
  await setPermissions(user, value);
  await refresh();
}

// ===============================================================
// Invitations

const inviteDialog = ref(false);
const inviteEmail = ref("");

async function submitInvite() {
  const email = inviteEmail.value.trim();
  if (!email) {
    return;
  }

  if (await invite(email)) {
    alert.success(i18n.t("household.invitation-sent"));
    inviteEmail.value = "";
    inviteDialog.value = false;
  }
  else {
    alert.error(i18n.t("household.invitation-failed"));
  }
}

// ===============================================================
// Removing members

const removeDialog = ref(false);
const removeTarget = ref<UserOut | null>(null);

function openRemove(user: UserOut) {
  removeTarget.value = user;
  removeDialog.value = true;
}

async function confirmRemove() {
  if (removeTarget.value) {
    await remove(removeTarget.value.id);
  }
  removeTarget.value = null;
}

onMounted(refresh);
</script>
