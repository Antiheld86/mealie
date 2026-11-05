<template>
  <v-select
    v-if="households.length > 1"
    v-model="model"
    :items="households"
    item-title="householdName"
    item-value="householdId"
    :label="label || $t('household.household')"
    :prepend-inner-icon="$globals.icons.household"
    :return-object="false"
    :disabled="disabled"
    hide-details
  />
</template>

<script setup lang="ts">
/**
 * Lets users who belong to several households choose which one an item (a meal plan entry, a shopping list)
 * is created in. It renders nothing for users with a single household, but still selects their primary one,
 * so the model always holds a household id.
 */
interface Props {
  label?: string;
  disabled?: boolean;
}
withDefaults(defineProps<Props>(), {
  label: "",
  disabled: false,
});

const model = defineModel<string | null>();

const { user } = useMealieAuth();
const households = computed(() => user.value?.households ?? []);

watchEffect(() => {
  if (model.value) {
    return;
  }

  const primary = households.value.find(household => household.isPrimary) ?? households.value[0];
  if (primary) {
    model.value = primary.householdId;
  }
});
</script>
