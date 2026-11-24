import type { ReactNode } from 'react';

/** Visible, accessible marker for fields required to complete the current action. */
export function RequiredMark() {
  return <><span aria-hidden="true" className="ml-1 font-semibold text-red-600">*</span><span className="sr-only"> (required)</span></>;
}

export function RequiredLabel({ children }: { children: ReactNode }) {
  return <>{children}<RequiredMark /></>;
}
