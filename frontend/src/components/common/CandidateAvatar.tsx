type AvatarGender = 'woman' | 'man' | 'non_binary' | 'prefer_not_to_say' | null | undefined;

export function CandidateAvatar({ gender, size = 44, label = 'Candidate avatar' }: { gender?: AvatarGender; size?: number; label?: string }) {
  const hair = gender === 'woman'
    ? <path d="M17 27c-1-10 3-16 11-16s12 6 11 16v8c-2-1-3-3-3-6v-5c-5 1-11 1-16 0v5c0 3-1 5-3 6z" fill="#475569" />
    : gender === 'man'
      ? <path d="M18 25c0-9 4-14 10-14s10 5 10 14c-4-3-7-4-10-4s-6 1-10 4z" fill="#475569" />
      : <path d="M18 25c0-9 4-14 10-14s10 5 10 14c-4-2-7-3-10-3s-6 1-10 3z" fill="#475569" />;
  return <svg width={size} height={size} viewBox="0 0 56 56" role="img" aria-label={label} className="shrink-0 rounded-full border border-slate-200 bg-violet-50">
    <circle cx="28" cy="28" r="28" fill="#EDE9FE" />
    {hair}
    <circle cx="28" cy="25" r="9" fill="#E8B99A" />
    <path d="M12 55c1-12 7-18 16-18s15 6 16 18" fill="#6D28D9" />
    <path d="M18 25c0-8 4-13 10-13" fill="none" stroke="#475569" strokeWidth="2" strokeLinecap="round" />
  </svg>;
}
