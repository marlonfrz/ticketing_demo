interface WindowEventMap {
  "admin-review-count-changed": CustomEvent<{
    pendingReviews?: number;
  }>;
  "admin-validation-count-changed": CustomEvent<{
    pendingValidationRequests?: number;
  }>;
}
