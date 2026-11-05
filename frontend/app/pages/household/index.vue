<template>
  <v-container
    v-if="household"
    class="narrow-container"
  >
    <BasePageTitle class="mb-5">
      <template #header>
        <v-img
          width="100%"
          max-height="100"
          max-width="100"
          src="/svgs/manage-group-settings.svg"
        />
      </template>
      <template #title>
        {{ $t("profile.household-settings") }}
      </template>
      {{ $t("profile.household-description") }}
    </BasePageTitle>
    <HouseholdContextSelect class="mb-4" />
    <v-form ref="refHouseholdEditForm" @submit.prevent="handleSubmit">
      <v-card variant="outlined" style="border-color: lightgray;">
        <v-card-text>
          <HouseholdPreferencesEditor v-if="household.preferences" v-model="household.preferences" />
        </v-card-text>
      </v-card>
      <div class="d-flex pa-2">
        <BaseButton type="submit" edit class="ml-auto">
          {{ $t("general.update") }}
        </BaseButton>
      </div>
    </v-form>
  </v-container>
</template>

<script setup lang="ts">
import HouseholdContextSelect from "~/components/Domain/Household/HouseholdContextSelect.vue";
import HouseholdPreferencesEditor from "~/components/Domain/Household/HouseholdPreferencesEditor.vue";
import { useHouseholdContext } from "~/composables/use-household-context";
import { useHouseholdSelf } from "~/composables/use-households";
import { alert } from "~/composables/use-toast";
import type { HouseholdInDB } from "~/lib/api/types/household";
import type { VForm } from "~/types/auto-forms";

definePageMeta({
  middleware: ["auth", "can-manage-household-only"],
});

const i18n = useI18n();
const { api, householdId, isPrimary } = useHouseholdContext();
// the cached copy of the user's primary household, which other pages read (e.g. the first day of the week)
const { actions: primaryHouseholdActions } = useHouseholdSelf();

useSeoMeta({
  title: i18n.t("household.household"),
});

// This page edits the household the user selected, which isn't necessarily their primary one. It always loads
// fresh data rather than the module-level cache of useHouseholdSelf(), which can be stale if the preferences
// were changed elsewhere (e.g. the Admin Households panel) in the same session.
const household = ref<HouseholdInDB | null>(null);

async function loadHousehold() {
  const { data } = await api.value.households.getCurrentUserHousehold();
  household.value = data;
}

watch(householdId, loadHousehold);
onMounted(loadHousehold);

const refHouseholdEditForm = ref<VForm | null>(null);

async function handleSubmit() {
  if (!refHouseholdEditForm.value?.validate() || !household.value?.preferences) {
    return;
  }

  const { data } = await api.value.households.setPreferences(household.value.preferences);
  if (data) {
    household.value.preferences = data;
    if (isPrimary.value) {
      await primaryHouseholdActions.refresh();
    }
    alert.success(i18n.t("settings.settings-updated"));
  }
  else {
    alert.error(i18n.t("settings.settings-update-failed"));
  }
}
</script>

<style lang="css">
.preference-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 600px;
}
</style>
