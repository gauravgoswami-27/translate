import { lazy, Suspense, useEffect, useState } from 'react';
import { api } from './api/client';
import { PAGES, Shell } from './components/Shell';
import { useTheme } from './lib/theme';
import ComparePage from './pages/ComparePage';
import GlossaryPage from './pages/GlossaryPage';
import ReaderPage from './pages/ReaderPage';
import TranslatePage from './pages/TranslatePage';
import { Skeleton } from './components/ui';

// Charts are heavy (recharts): load the Results page only when it is opened.
const ResultsPage = lazy(() => import('./pages/ResultsPage'));

const pageFromHash = () => {
  const id = window.location.hash.replace('#', '');
  return PAGES.some((p) => p.id === id) ? id : 'translate';
};

/** Polls /health; status: 'checking' | 'online' | 'offline'. */
function useApiHealth() {
  const [health, setHealth] = useState({ status: 'checking', data: null });
  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const data = await api.health();
        if (alive) setHealth({ status: 'online', data });
      } catch {
        if (alive) setHealth({ status: 'offline', data: null });
      }
    };
    check();
    const id = setInterval(check, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);
  return health;
}

export default function App() {
  const [page, setPage] = useState(pageFromHash);
  const theme = useTheme();
  const health = useApiHealth();

  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const Page = { translate: TranslatePage, compare: ComparePage, results: ResultsPage, glossary: GlossaryPage, reader: ReaderPage }[page];
  return (
    <Shell page={page} setPage={setPage} theme={theme} health={health}>
      <Suspense
        fallback={
          <div className="space-y-4">
            <Skeleton className="h-9 w-64" />
            <Skeleton className="h-80 w-full" />
          </div>
        }
      >
        <Page health={health} />
      </Suspense>
    </Shell>
  );
}
