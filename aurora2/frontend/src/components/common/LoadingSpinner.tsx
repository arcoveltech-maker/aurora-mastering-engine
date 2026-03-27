interface Props {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' };

export function LoadingSpinner({ size = 'md', label }: Props) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className={`${sizes[size]} border-2 border-aurora-accent/30 border-t-aurora-accent rounded-full animate-spin`} />
      {label && <span className="text-xs text-white/50">{label}</span>}
    </div>
  );
}
