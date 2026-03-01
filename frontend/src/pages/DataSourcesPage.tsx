/**
 * DataSourcesPage
 *
 * Admin page for managing external data source connections.
 */

import { DataSourceManager } from '../components/admin/DataSourceManager';

export function DataSourcesPage() {
  return (
    <div className="max-w-7xl mx-auto py-8">
      <DataSourceManager />
    </div>
  );
}
