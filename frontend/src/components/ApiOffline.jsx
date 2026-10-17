import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { API_BASE_URL, START_COMMAND } from '../api/client';
import { Alert, Button } from './ui';

export default function ApiOffline({ error }) {
  const [copied, setCopied] = useState(false);
  if (error && !error.offline) {
    return (
      <Alert tone="bad" title="Translation failed">
        {error.message}
      </Alert>
    );
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(START_COMMAND);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard blocked: the command is visible anyway */
    }
  }
  return (
    <Alert tone="warn" title={`The translation API isn't running at ${API_BASE_URL}`}>
      <p>Start it from the repository root (the first request then loads the model, which can take a minute):</p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <code className="min-w-0 flex-1 break-all rounded-lg bg-surface px-3 py-2 font-mono text-xs text-ink">{START_COMMAND}</code>
        <Button size="sm" variant="secondary" icon={copied ? Check : Copy} onClick={copy}>
          {copied ? 'Copied' : 'Copy'}
        </Button>
      </div>
    </Alert>
  );
}
