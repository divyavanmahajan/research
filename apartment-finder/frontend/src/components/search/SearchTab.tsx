import { SearchPanel } from './SearchPanel';
import { SearchResults } from './SearchResults';

export function SearchTab() {
  return (
    <div className="search-tab">
      <SearchPanel />
      <SearchResults />
    </div>
  );
}
