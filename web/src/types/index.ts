export interface SumDistributionItem {
  sum: number;
  ways: number;
  prob_theoretical: number;
  observed: number;
  expected: number;
  ratio: number;
  z_score: number;
  ci_95_lower: number;
  ci_95_upper: number;
}

export interface Chi2TestItem {
  n: number;
  chi2: number;
  df: number;
  p_value: number;
  is_significant: boolean;
}

export interface StatsResult {
  metadata: {
    data_hash: string;
    total_draws: number;
    version: string;
    seed: number;
    computed_at: string;
  };
  m1_m2_distribution: {
    n: number;
    distribution: Record<string, SumDistributionItem>;
  };
  m3_chi2_tests: {
    sums_df15: Chi2TestItem;
    dice_df5: Chi2TestItem;
    ordered_216_df215: Chi2TestItem;
    unordered_56_df55: Chi2TestItem;
  };
  m8_date_analysis: {
    num_days: number;
    sum_outlier_tests: Record<
      string,
      {
        outlier_days: number;
        expected_outlier_days: number;
        p_value: number;
        is_anomalous: boolean;
      }
    >;
    total_outlier_instances: number;
  };
}
