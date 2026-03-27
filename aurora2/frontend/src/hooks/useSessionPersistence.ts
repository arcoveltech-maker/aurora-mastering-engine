import { useCallback } from 'react';
import { useSessionStore } from '@/stores/sessionStore';
import { useProcessingStore } from '@/stores/processingStore';
import { api } from '@/utils/api';
import { useToast } from '@/contexts/ToastContext';

export function useSessionPersistence(token: string | null) {
  const { manifest, sessionId, setSessionId, setVersionId, setLastSaved, patchManifest } = useSessionStore();
  const { pushUndo } = useProcessingStore();
  const { addToast } = useToast();

  const save = useCallback(async () => {
    if (!manifest || !token) return;

    try {
      if (sessionId) {
        const res = await api.sessions.update(token, sessionId, manifest as Record<string, unknown>);
        setVersionId(res.version_id);
      } else {
        const res = await api.sessions.create(token, manifest as Record<string, unknown>);
        setSessionId(res.session_id);
        setVersionId(res.version_id);
      }
      setLastSaved(new Date().toISOString());
      addToast({ type: 'success', message: 'Session saved' });
    } catch {
      addToast({ type: 'error', message: 'Failed to save session' });
    }
  }, [manifest, token, sessionId, setSessionId, setVersionId, setLastSaved, addToast]);

  const updateMacro = useCallback((key: string, value: number) => {
    if (!manifest) return;
    pushUndo(JSON.stringify(manifest));
    patchManifest({ macros: { ...manifest.macros, [key]: value } });
  }, [manifest, patchManifest, pushUndo]);

  return { save, updateMacro };
}
