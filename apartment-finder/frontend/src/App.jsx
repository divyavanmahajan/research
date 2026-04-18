import { Routes, Route, NavLink } from 'react-router-dom';
import ListView from './views/ListView';
import DetailView from './views/DetailView';
import InvestigateView from './views/InvestigateView';
import MapView from './views/MapView';
import ErrorBoundary from './components/ErrorBoundary';

function NavItem({ to, label }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `px-3 py-1 rounded-md text-sm font-medium transition-colors ${
          isActive ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900'
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="h-14 bg-white border-b border-gray-200 flex items-center px-4 gap-1 sticky top-0 z-50">
        <span className="font-semibold text-gray-900 mr-4">🏠 Apartment Finder</span>
        <NavItem to="/" label="My List" />
        <NavItem to="/investigate" label="Investigate" />
        <NavItem to="/map" label="Map" />
      </nav>
      <main>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<ListView />} />
            <Route path="/apartment/:id" element={<DetailView />} />
            <Route path="/investigate" element={<InvestigateView />} />
            <Route path="/map" element={<MapView />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  );
}
