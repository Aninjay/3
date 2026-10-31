import React from 'react';
import { 
  LayoutDashboard, Calendar, Users, Award,
  ShieldCheck, LogOut, CheckSquare, Clock, UserRoundCog
} from 'lucide-react';

export function Sidebar({ currentView, setView, user, onLogout }) {
  const isOrganizer = user?.role === 'convener' || user?.role === 'co_convener';
  const isCoreCommittee = user?.role === 'core_committee';

  const organizerNav = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'events', label: 'Events & Staffing', icon: Calendar },
    { id: 'volunteers', label: 'Volunteers Roster', icon: Users },
    { id: 'core-committee', label: 'Manage Core Committee', icon: UserRoundCog },
    { id: 'skills', label: 'Skills Catalog', icon: Award },
    { id: 'audit', label: 'Audit History', icon: ShieldCheck }
  ];

  const volunteerNav = [
    { id: 'my-assignments', label: 'My Assignments', icon: CheckSquare },
    { id: 'my-skills', label: 'My Skills', icon: Award },
    { id: 'my-history', label: 'Assignment History', icon: Clock }
  ];

  const coreCommitteeNav = [
    { id: 'core-dashboard', label: 'My Departments', icon: LayoutDashboard }
  ];

  const navItems = isOrganizer ? organizerNav : isCoreCommittee ? coreCommitteeNav : volunteerNav;

  return (
    <aside style={{
      width: '240px',
      backgroundColor: '#FFFFFF',
      borderRight: '1px solid var(--color-border)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0
    }}>
      {/* Brand Header */}
      <div style={{
        padding: '20px 20px 16px',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px'
      }}>
        <img
          src="/assets/tapmi-logo.png"
          alt="TAPMI — Manipal Academy of Higher Education"
          style={{ display: 'block', width: '100%', maxWidth: '190px', height: 'auto', objectFit: 'contain' }}
        />
        <div style={{ fontSize: '11.5px', color: 'var(--color-muted)' }}>
          Volunteer Allocation System
        </div>
      </div>

      {/* Navigation Links */}
      <nav style={{ padding: '16px 10px', flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                width: '100%',
                padding: '9px 12px',
                borderRadius: 'var(--radius-md)',
                border: 'none',
                background: isActive ? 'var(--color-primary-soft)' : 'transparent',
                color: isActive ? 'var(--color-primary-hover)' : 'var(--color-text)',
                fontWeight: isActive ? 600 : 400,
                fontSize: '13.5px',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background-color 0.1s ease'
              }}
            >
              <Icon size={17} color={isActive ? 'var(--color-primary)' : 'var(--color-muted)'} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* User Footer */}
      <div style={{
        padding: '16px',
        borderTop: '1px solid var(--color-border)',
        backgroundColor: 'var(--color-subtle)'
      }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text)', truncate: 'true' }}>
          {user?.email}
        </div>
        <div style={{
          fontSize: '11px',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          color: 'var(--color-primary)',
          fontWeight: 600,
          marginTop: '2px',
          marginBottom: '10px'
        }}>
          {user?.role?.replace('_', ' ')}
        </div>
        <button
          onClick={onLogout}
          className="btn btn-secondary btn-sm"
          style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
        >
          <LogOut size={14} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
