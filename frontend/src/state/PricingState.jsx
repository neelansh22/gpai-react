import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { pricingEndpoints } from "../api/pricingClient";

const PricingContext = createContext(null);

export function PricingStateProvider({ children }) {
  const [filterOptions, setFilterOptions] = useState({
    part_classes: [],
    conditions: [],
    years: [],
    part_numbers: [],
  });
  const [filters, setFilters] = useState({
    part_class: [],
    condition: [],
    year: [],
    part_number: [],
  });
  const [loadingOptions, setLoadingOptions] = useState(true);

  useEffect(() => {
    pricingEndpoints
      .filters()
      .then((res) => setFilterOptions(res.data))
      .finally(() => setLoadingOptions(false));
  }, []);

  const toggleFilter = useCallback((key, value) => {
    setFilters((prev) => {
      const current = prev[key] || [];
      const exists = current.includes(value);
      const next = exists ? current.filter((v) => v !== value) : [...current, value];
      return { ...prev, [key]: next };
    });
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({ part_class: [], condition: [], year: [], part_number: [] });
  }, []);

  const activeFilterCount = useMemo(
    () => Object.values(filters).reduce((sum, arr) => sum + arr.length, 0),
    [filters]
  );

  const value = {
    filterOptions,
    loadingOptions,
    filters,
    setFilters,
    toggleFilter,
    clearFilters,
    activeFilterCount,
  };

  return <PricingContext.Provider value={value}>{children}</PricingContext.Provider>;
}

export function usePricingState() {
  const ctx = useContext(PricingContext);
  if (!ctx) throw new Error("usePricingState must be used within PricingStateProvider");
  return ctx;
}
