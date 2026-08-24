import { NavLink } from 'react-router-dom';
import './Sidebar.css';

const Sidebar = () => {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="logo-icon">✨</div>
        <h2>Nova</h2>
      </div>
      
      <nav className="sidebar-nav">
        <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>
          <span className="nav-icon">📊</span>
          Overview
        </NavLink>
        <NavLink to="/recovery" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">📋</span>
          Recovery Queue
        </NavLink>
        <NavLink to="/audit" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">📄</span>
          Audit Trail
        </NavLink>
        <NavLink to="/comparison" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">⚖️</span>
          Comparison
        </NavLink>
        <NavLink to="/strategy" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">🎯</span>
          Strategy
        </NavLink>
      </nav>

      <div className="sidebar-bottom">
        <a href="#settings" className="nav-item">
          <span className="nav-icon">⚙️</span>
          Settings
        </a>
      </div>
    </div>
  );
};

export default Sidebar;
