<template>
  <v-select
    v-if="households.length > 1"
    :model-value="householdId"
    :items="households"
    item-title="householdName"
    item-value="householdId"
    :label="$t('household.household')"
    :prepend-inner-icon="$globals.icons.household"
    :return-object="false"
    hide-details
    @update:model-value="select"
  />
</template>

<script setup lang="ts">
import { useHouseholdContext } from "~/composables/use-household-context";

/**
 * Chooses which household a household management page acts on, and keeps the choice in the URL
 * (`?householdId=`). Renders nothing for users who belong to a single household.
 */
const { households, householdId, select } = useHouseholdContext();
</script>
