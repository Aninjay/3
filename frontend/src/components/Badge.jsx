import React from 'react';

export function Badge({ type = 'normal', children }) {
  const normType = (type || 'normal').toLowerCase();
  let badgeClass = 'badge-normal';

  if (normType === 'critical') badgeClass = 'badge-critical';
  else if (normType === 'high') badgeClass = 'badge-high';
  else if (normType === 'success' || normType === 'published' || normType === 'active') badgeClass = 'badge-success';
  else if (normType === 'approved') badgeClass = 'badge-approved';
  else if (normType === 'draft') badgeClass = 'badge-draft';
  else if (normType === 'danger' || normType === 'cancelled' || normType === 'rejected') badgeClass = 'badge-critical';

  return (
    <span className={`badge ${badgeClass}`}>
      {children}
    </span>
  );
}
