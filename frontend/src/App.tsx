import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { HomePage } from './pages/HomePage';
import { EvaluatorPage } from './pages/EvaluatorPage';
import { WizardPage } from './pages/WizardPage';
import { EditorPage } from './pages/EditorPage';
import { RuleEditorPage } from './components/editor/RuleEditorPage';
import { SavedPoliciesPage } from './pages/SavedPoliciesPage';
import { NotFoundPage } from './pages/NotFoundPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<HomePage />} />
                <Route path="/evaluator" element={<EvaluatorPage />} />
                <Route path="/saved-policies" element={<SavedPoliciesPage />} />
                <Route element={<ProtectedRoute requiredRole="admin" />}>
                  <Route path="/generator" element={<WizardPage />} />
                  <Route path="/editor" element={<EditorPage />} />
                  <Route path="/editor/:ruleId" element={<RuleEditorPage />} />
                </Route>
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}

export default App;
