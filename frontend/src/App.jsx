import React, { useState, useEffect } from 'react';
import { api, setToken } from './api/client';
import { CampusLogin } from './components/CampusLogin';
import { Sidebar } from './components/Sidebar';
import { OrganizerDashboard } from './pages/OrganizerDashboard';
import { EventsPage } from './pages/EventsPage';
import { EventDetailPage } from './pages/EventDetailPage';
import { VolunteersPage } from './pages/VolunteersPage';
import { SkillsPage } from './pages/SkillsPage';
import { AuditLogPage } from './pages/AuditLogPage';
import { VolunteerPortal } from './pages/VolunteerPortal';
import { CoreCommitteeManagementPage } from './pages/CoreCommitteeManagementPage';
import { CoreCommitteeDashboard } from './pages/CoreCommitteeDashboard';

function getInitialView(role) {
  if (role === 'volunteer') return 'my-assignments';
  if (role === 'core_committee') return 'core-dashboard';
  return 'dashboard';
}

export function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentView, setCurrentView] = useState('dashboard');
  const [selectedEventId, setSelectedEventId] = useState(null);

  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await api.getMe();
        setUser(res.data);
        setCurrentView(getInitialView(res.data.role));
      } catch (err) {
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    checkAuth();
  }, []);

  useEffect(() => {
    function handleExpiredSession() {
      setToken(null);
      setUser(null);
      setCurrentView('dashboard');
      setSelectedEventId(null);
    }
    window.addEventListener('tapmi:unauthorized', handleExpiredSession);
    return () => window.removeEventListener('tapmi:unauthorized', handleExpiredSession);
  }, []);

  function handleLoginSuccess(userData) {
    setUser(userData);
    setCurrentView(getInitialView(userData.role));
  }

  function handleLogout() {
    api.logout().catch(() => {});
    setToken(null);
    setUser(null);
    setCurrentView('dashboard');
    setSelectedEventId(null);
  }

  function handleSelectEvent(id) {
    setSelectedEventId(id);
    setCurrentView('event-detail');
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#FFFFFF' }}>
        <div style={{ textAlign: 'center', color: 'var(--color-muted)', fontSize: '14px' }}>
          Initializing TAPMI Cultural Committee System...
        </div>
      </div>
    );
  }

  // Unauthenticated user -> display TAPMI Campus Login page
  if (!user) {
    return <CampusLogin onLoginSuccess={handleLoginSuccess} />;
  }

  const isOrganizer = user.role === 'convener' || user.role === 'co_convener';
  const isCoreCommittee = user.role === 'core_committee';

  return (
    <div className="app-container">
      {/* Sidebar navigation */}
      <Sidebar
        currentView={currentView}
        setView={(v) => {
          setSelectedEventId(null);
          setCurrentView(v);
        }}
        user={user}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <main className="main-content">
        <div className="page-body">
          {/* Organizer Views */}
          {isOrganizer && (
            <>
              {currentView === 'dashboard' && (
                <OrganizerDashboard
                  onSelectEvent={handleSelectEvent}
                  onManageCoreCommittee={() => setCurrentView('core-committee')}
                />
              )}
              {currentView === 'events' && (
                <EventsPage onSelectEvent={handleSelectEvent} />
              )}
              {currentView === 'event-detail' && selectedEventId && (
                <EventDetailPage
                  eventId={selectedEventId}
                  onBack={() => setCurrentView('events')}
                />
              )}
              {currentView === 'volunteers' && <VolunteersPage />}
              {currentView === 'skills' && <SkillsPage />}
              {currentView === 'audit' && <AuditLogPage />}
              {currentView === 'core-committee' && <CoreCommitteeManagementPage />}
            </>
          )}

          {isCoreCommittee && currentView === 'core-dashboard' && <CoreCommitteeDashboard />}

          {/* Volunteer Views */}
          {user.role === 'volunteer' && (
            <VolunteerPortal activeTab={currentView} />
          )}
        </div>
      </main>
    </div>
  );
}
export default App;
