<template>
  <div>
    <h3 class="text-h6">
      {{ $t("household.memberships") }}
    </h3>
    <p class="text-medium-emphasis mb-2">
      {{ $t("household.memberships-description") }}
    </p>
    <v-table density="compact">
      <thead>
        <tr>
          <th>{{ $t("household.household") }}</th>
          <th class="text-center">
            {{ $t("household.additional-member") }}
          </th>
          <th class="text-center">
            {{ $t("household.can-manage-household") }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="household in households"
          :key="household.id"
        >
          <td>
            {{ household.name }}
            <v-chip
              v-if="household.id === primaryHouseholdId"
              class="ms-2"
              size="x-small"
              label
              color="primary"
            >
              {{ $t("household.primary-household") }}
            </v-chip>
          </td>
          <td>
            <div class="d-flex justify-center">
              <v-checkbox
                :data-test="`member-${household.id}`"
                :model-value="isMember(household.id)"
                :disabled="household.id === primaryHouseholdId"
                color="primary"
                hide-details
                @update:model-value="setMember(household.id, !!$event)"
              />
            </div>
          </td>
          <td>
            <div class="d-flex justify-center">
              <v-switch
                :data-test="`manager-${household.id}`"
                :model-value="canManage(household.id)"
                :disabled="!isMember(household.id)"
                color="primary"
                density="compact"
                hide-details
                @update:model-value="setManager(household.id, !!$event)"
              />
            </div>
          </td>
        </tr>
      </tbody>
    </v-table>
  </div>
</template>

<script setup lang="ts">
import type { UserHouseholdMembershipUpdate } from "~/lib/api/types/user";

interface HouseholdOption {
  id: string;
  name: string;
}

/**
 * The households a user belongs to and whether they can manage each. The primary household is chosen elsewhere
 * (it decides where the user's recipes live); it is always one of the memberships and can't be removed here.
 */
const props = defineProps<{
  /** The households of the user's group */
  households: HouseholdOption[];
  primaryHouseholdId: string;
}>();

const memberships = defineModel<UserHouseholdMembershipUpdate[]>({ required: true });

function find(householdId: string) {
  return memberships.value.find(membership => membership.householdId === householdId);
}

const isMember = (householdId: string) => !!find(householdId);
const canManage = (householdId: string) => !!find(householdId)?.canManageHousehold;

function setMember(householdId: string, member: boolean) {
  if (member === isMember(householdId)) {
    return;
  }
  memberships.value = member
    ? [...memberships.value, { householdId, canManageHousehold: false }]
    : memberships.value.filter(membership => membership.householdId !== householdId);
}

function setManager(householdId: string, value: boolean) {
  memberships.value = memberships.value.map(membership =>
    membership.householdId === householdId ? { ...membership, canManageHousehold: value } : membership,
  );
}

// whoever picks a new primary household becomes a member of it
watch(() => props.primaryHouseholdId, (primary) => {
  if (primary) {
    setMember(primary, true);
  }
});
</script>
