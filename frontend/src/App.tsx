import React, { useState, useEffect } from 'react';
import { api, UserProfile, Deadline, RecoveryPlan } from './services/api';

export default function App() {
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [selectedDeadline, setSelectedDeadline] = useState<Deadline | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'create' | 'profile'>('dashboard');
  
  // Panic Modal State
  const [isPanicModalOpen, setIsPanicModalOpen] = useState(false);
  const [panicLostHours, setPanicLostHours] = useState<number>(2);
  const [panicReason, setPanicReason] = useState('');
  const [recoveryPlan, setRecoveryPlan] = useState<RecoveryPlan | null>(null);
  const [panicLoading, setPanicLoading] = useState(false);

  // Form State
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newDueDate, setNewDueDate] = useState('');
  const [newHours, setNewHours] = useState('');
  const [newCategory, setNewCategory] = useState('study');
  const [formLoading, setFormLoading] = useState(false);

  // Profile Form State
  const [profName, setProfName] = useState('');
  const [profStart, setProfStart] = useState('09:00');
  const [profEnd, setProfEnd] = useState('18:00');
  const [profEnergy, setProfEnergy] = useState('consistent');
  const [profStress, setProfStress] = useState('break_into_tiny_steps');
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const prof = await api.getProfile();
      setProfile(prof);
      setProfName(prof.name);
      setProfStart(prof.working_hours_start);
      setProfEnd(prof.working_hours_end);
      setProfEnergy(prof.energy_profile);
      setProfStress(prof.stress_handling);

      const dls = await api.getDeadlines();
      setDeadlines(dls);
      if (dls.length > 0) {
        setSelectedDeadline(dls[0]);
      }
    } catch (err) {
      console.error("Error loading startup data:", err);
    }
  };

  const handleSelectDeadline = async (id: string) => {
    try {
      const dl = await api.getDeadline(id);
      setSelectedDeadline(dl);
      setRecoveryPlan(null); // Reset active recovery plan view
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateDeadline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newDueDate) return;
    setFormLoading(true);
    try {
      const created = await api.createDeadline({
        title: newTitle,
        description: newDesc,
        due_date: newDueDate,
        estimated_hours: newHours ? parseFloat(newHours) : undefined,
        category: newCategory
      });
      setDeadlines(prev => [...prev, created]);
      setSelectedDeadline(created);
      setActiveTab('dashboard');
      
      // Reset form
      setNewTitle('');
      setNewDesc('');
      setNewDueDate('');
      setNewHours('');
      setNewCategory('study');
    } catch (err) {
      alert("Failed to decompose and create schedule. Please check server.");
    } finally {
      setFormLoading(false);
    }
  };

  const handleToggleSubtask = async (subtaskId: string, currentStatus: string) => {
    if (!selectedDeadline) return;
    let nextStatus: 'todo' | 'in_progress' | 'done' = 'todo';
    if (currentStatus === 'todo') nextStatus = 'in_progress';
    else if (currentStatus === 'in_progress') nextStatus = 'done';

    try {
      const updated = await api.updateSubtaskStatus(selectedDeadline.id, subtaskId, nextStatus);
      
      // Update local lists
      setDeadlines(prev => prev.map(d => d.id === updated.id ? updated : d));
      setSelectedDeadline(updated);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteDeadline = async (id: string) => {
    if (!confirm("Are you sure you want to delete this deadline and its schedule?")) return;
    try {
      await api.deleteDeadline(id);
      const remaining = deadlines.filter(d => d.id !== id);
      setDeadlines(remaining);
      if (remaining.length > 0) {
        setSelectedDeadline(remaining[0]);
      } else {
        setSelectedDeadline(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handlePanicTrigger = async () => {
    if (!selectedDeadline) return;
    setPanicLoading(true);
    try {
      const plan = await api.triggerPanic(selectedDeadline.id, {
        current_time: new Date().toISOString(),
        lost_hours: panicLostHours,
        custom_panic_reason: panicReason
      });
      setRecoveryPlan(plan);
      
      // Refresh current deadline details
      const refreshed = await api.getDeadline(selectedDeadline.id);
      setDeadlines(prev => prev.map(d => d.id === refreshed.id ? refreshed : d));
      setSelectedDeadline(refreshed);
      setIsPanicModalOpen(false);
      
      // Reset inputs
      setPanicReason('');
      setPanicLostHours(2);
    } catch (err) {
      alert("Failed to trigger recovery schedule calculation.");
    } finally {
      setPanicLoading(false);
    }
  };

  const handleForceReschedule = async () => {
    if (!selectedDeadline) return;
    try {
      const updated = await api.rescheduleDeadline(selectedDeadline.id);
      setDeadlines(prev => prev.map(d => d.id === updated.id ? updated : d));
      setSelectedDeadline(updated);
      alert("Schedule successfully re-aligned to current time!");
    } catch (err) {
      console.error(err);
    }
  };

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileLoading(true);
    try {
      const updated = await api.updateProfile({
        name: profName,
        working_hours_start: profStart,
        working_hours_end: profEnd,
        energy_profile: profEnergy,
        stress_handling: profStress
      });
      setProfile(updated);
      
      // Refresh deadlines as they might have been rescheduled
      const dls = await api.getDeadlines();
      setDeadlines(dls);
      if (selectedDeadline) {
        const found = dls.find(d => d.id === selectedDeadline.id);
        if (found) setSelectedDeadline(found);
      }
      alert("Bio settings saved! Active schedules rescheduled dynamically.");
    } catch (err) {
      alert("Failed to update profile.");
    } finally {
      setProfileLoading(false);
    }
  };

  // Helper formatting dates
  const formatTime = (isoString?: string) => {
    if (!isoString) return '--:--';
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '--/--';
    const date = new Date(isoString);
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  // Compute progress
  const getProgress = (dl: Deadline) => {
    if (!dl.subtasks || dl.subtasks.length === 0) return 0;
    const completed = dl.subtasks.filter(s => s.status === 'done').length;
    return Math.round((completed / dl.subtasks.length) * 100);
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div>
          <div className="brand-section">
            <div className="brand-logo">⚡</div>
            <h1 className="brand-name">LifeSaver</h1>
          </div>
          
          <nav>
            <ul className="nav-links">
              <li>
                <div 
                  className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
                  onClick={() => setActiveTab('dashboard')}
                >
                  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/></svg>
                  Dashboard
                </div>
              </li>
              <li>
                <div 
                  className={`nav-item ${activeTab === 'create' ? 'active' : ''}`}
                  onClick={() => setActiveTab('create')}
                >
                  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4"/></svg>
                  New Deadline
                </div>
              </li>
              <li>
                <div 
                  className={`nav-item ${activeTab === 'profile' ? 'active' : ''}`}
                  onClick={() => setActiveTab('profile')}
                >
                  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                  Bio Settings
                </div>
              </li>
            </ul>
          </nav>
        </div>

        {/* User Bio Status Card */}
        {profile && (
          <div className="user-widget">
            <div className="user-widget-title">Active Profile</div>
            <div className="user-widget-name">{profile.name}</div>
            <div className="user-widget-details">
              🕒 {profile.working_hours_start} - {profile.working_hours_end}<br/>
              ⚡ {profile.energy_profile.replace('_', ' ')}
            </div>
          </div>
        )}
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        
        {/* DASHBOARD TAB */}
        {activeTab === 'dashboard' && (
          <div>
            <div className="header-section">
              <div>
                <h2 className="header-title">Productivity Core</h2>
                <div className="header-subtitle">Intelligent planning & recovery assistant</div>
              </div>
              
              <div style={{ display: 'flex', gap: '1rem' }}>
                {deadlines.length > 0 && selectedDeadline && (
                  <button 
                    className="btn btn-panic" 
                    onClick={() => setIsPanicModalOpen(true)}
                  >
                    🚨 PANIC BUTTON
                  </button>
                )}
                <button className="btn btn-primary" onClick={() => setActiveTab('create')}>
                  + Add Goal
                </button>
              </div>
            </div>

            {/* Welcome banner if no deadlines */}
            {deadlines.length === 0 ? (
              <div className="glass-panel card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>No Active Deadlines!</h3>
                <p style={{ color: 'hsl(var(--text-secondary))', marginBottom: '2rem', maxWidth: '500px', marginInline: 'auto' }}>
                  Great job keeping on track! When you have a new last-minute project or test coming up, add it here. Gemini will break it down into micro-steps and budget your time.
                </p>
                <button className="btn btn-primary" onClick={() => setActiveTab('create')}>
                  Get Started
                </button>
              </div>
            ) : (
              <div>
                {/* Deadline selection dropdown */}
                <div className="glass-panel" style={{ padding: '1rem', marginBottom: '2rem', display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Select Deadline:</span>
                  <div style={{ display: 'flex', gap: '0.5rem', flexGrow: 1, overflowX: 'auto' }}>
                    {deadlines.map(dl => (
                      <button 
                        key={dl.id}
                        className={`btn ${selectedDeadline?.id === dl.id ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                        onClick={() => handleSelectDeadline(dl.id)}
                      >
                        {dl.title} ({getProgress(dl)}%)
                      </button>
                    ))}
                  </div>
                </div>

                {selectedDeadline && (
                  <div>
                    {/* Active Deadline Details */}
                    <div className="glass-panel card" style={{ borderLeft: selectedDeadline.status === 'panicked' ? '4px solid hsl(var(--accent))' : '4px solid hsl(var(--primary))' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                            <h3 style={{ fontSize: '1.6rem' }}>{selectedDeadline.title}</h3>
                            <span className={`status-pill status-${selectedDeadline.status}`}>
                              {selectedDeadline.status}
                            </span>
                          </div>
                          <p style={{ color: 'hsl(var(--text-secondary))', marginBottom: '1rem' }}>{selectedDeadline.description}</p>
                          <div className="task-meta">
                            <span>📅 Due: <strong>{formatDate(selectedDeadline.due_date)} @ {formatTime(selectedDeadline.due_date)}</strong></span>
                            <span>⏳ Estimate: <strong>{selectedDeadline.estimated_hours} hrs</strong></span>
                            <span>🏷️ Category: <strong>{selectedDeadline.category}</strong></span>
                          </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
                          <button 
                            className="btn btn-secondary" 
                            style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                            onClick={() => handleForceReschedule()}
                          >
                            🔄 Re-align Schedule
                          </button>
                          <button 
                            className="btn" 
                            style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#f87171', fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                            onClick={() => handleDeleteDeadline(selectedDeadline.id)}
                          >
                            Delete Goal
                          </button>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div style={{ marginTop: '1.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                          <span>Completion Progress</span>
                          <span style={{ fontWeight: 600 }}>{getProgress(selectedDeadline)}%</span>
                        </div>
                        <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                          <div 
                            style={{ 
                              width: `${getProgress(selectedDeadline)}%`, 
                              height: '100%', 
                              background: selectedDeadline.status === 'panicked' ? 'linear-gradient(to right, #ff0055, #ff7300)' : 'linear-gradient(to right, hsl(var(--primary)), hsl(var(--secondary)))',
                              transition: 'width 0.4s ease'
                            }} 
                          />
                        </div>
                      </div>
                    </div>

                    {/* Triage / Recovery Plan Notification (if panicked) */}
                    {selectedDeadline.status === 'panicked' && (
                      <div className="glass-panel card triage-strategy-container" style={{ marginBottom: '2rem' }}>
                        <h4 style={{ color: 'hsl(var(--accent))', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          🚨 AI RECOVERY STRATEGY ACTIVE
                        </h4>
                        <p className="triage-strategy-text">
                          {recoveryPlan?.triage_strategy || "Gemini has re-calibrated your deliverables to meet the tight deadline. Low importance subtasks are capped or skipped. Focus on the revised schedule below."}
                        </p>
                        {recoveryPlan?.motivation_tip && (
                          <div style={{ marginTop: '1rem', fontStyle: 'italic', color: 'hsl(var(--secondary))', fontWeight: 500 }}>
                            💡 {recoveryPlan.motivation_tip}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Main Timeline and Subtasks columns */}
                    <div className="dashboard-grid">
                      {/* Left: Schedule Timeline */}
                      <div className="glass-panel card">
                        <h4 className="card-title">Hourly Timeline</h4>
                        <div className="timeline-container">
                          {selectedDeadline.subtasks && selectedDeadline.subtasks.filter(s => s.status !== 'skipped').map((task) => (
                            <div 
                              key={task.id} 
                              className="timeline-slot"
                              style={{ 
                                '--slot-color': task.status === 'done' ? 'hsl(var(--success))' : (task.importance === 3 ? 'hsl(var(--accent))' : (task.importance === 2 ? 'hsl(var(--secondary))' : 'hsl(var(--primary))')),
                                opacity: task.status === 'done' ? 0.6 : 1
                              } as React.CSSProperties}
                            >
                              <div className="timeline-time">
                                <span style={{ fontWeight: 600 }}>{formatDate(task.scheduled_start)}</span>
                                <span style={{ fontSize: '0.8rem', color: 'hsl(var(--text-muted))' }}>
                                  {formatTime(task.scheduled_start)} - {formatTime(task.scheduled_end)}
                                </span>
                              </div>
                              <div className="timeline-task">
                                <div className="task-title" style={{ textDecoration: task.status === 'done' ? 'line-through' : 'none' }}>
                                  {task.title}
                                </div>
                                <div className="task-meta">
                                  <span>⌛ {task.duration_hours} hrs</span>
                                  <span className={`importance-badge importance-${task.importance}`}>
                                    {task.importance === 3 ? 'CRITICAL' : (task.importance === 2 ? 'MEDIUM' : 'LOW')}
                                  </span>
                                  {task.status !== 'todo' && (
                                    <span style={{ color: task.status === 'done' ? 'hsl(var(--success))' : 'hsl(var(--primary))', fontWeight: 600 }}>
                                      {task.status.toUpperCase()}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Right: Subtasks Checklist */}
                      <div className="glass-panel card">
                        <h4 className="card-title">Checklist Kanban</h4>
                        <div className="subtasks-list">
                          {selectedDeadline.subtasks && selectedDeadline.subtasks.map(task => (
                            <div 
                              key={task.id} 
                              className={`subtask-item ${task.status}`}
                              style={{ 
                                borderLeft: task.status === 'done' ? '3px solid hsl(var(--success))' : (task.status === 'in_progress' ? '3px solid hsl(var(--primary))' : '3px solid transparent'),
                                opacity: task.status === 'skipped' ? 0.4 : 1
                              }}
                            >
                              <div className="subtask-content">
                                {task.status !== 'skipped' && (
                                  <div 
                                    className={`checkbox-custom ${task.status === 'done' ? 'checked' : ''}`}
                                    onClick={() => handleToggleSubtask(task.id, task.status)}
                                  />
                                )}
                                <div>
                                  <span className="subtask-text">{task.title}</span>
                                  <div style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))', marginTop: '0.2rem' }}>
                                    Duration: {task.duration_hours} hrs | Priority: {task.importance === 3 ? 'High' : (task.importance === 2 ? 'Medium' : 'Low')}
                                    {task.status === 'skipped' && <span style={{ color: 'hsl(var(--accent))', marginLeft: '0.5rem' }}>(Triage: Skipped)</span>}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* CREATE DEADLINE TAB */}
        {activeTab === 'create' && (
          <div className="glass-panel card" style={{ maxWidth: '700px', marginInline: 'auto' }}>
            <h3 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>Create AI-Powered Goal</h3>
            <p style={{ color: 'hsl(var(--text-secondary))', marginBottom: '2rem' }}>
              Define your final target and details. Gemini will analyze the requirements, decompose the deliverables, and schedule tasks based on your energy profile and working windows.
            </p>
            
            <form onSubmit={handleCreateDeadline}>
              <div className="form-group">
                <label className="form-label">Goal / Deadline Title</label>
                <input 
                  type="text" 
                  className="form-input" 
                  placeholder="e.g. Write Hackathon Final Demo Pitch" 
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Detailed Scope & Requirements</label>
                <textarea 
                  className="form-input" 
                  style={{ minHeight: '120px', resize: 'vertical' }}
                  placeholder="Write details of what needs to be done. The more detailed, the better Gemini can plan. Mention key sections, libraries, or outputs required."
                  value={newDesc}
                  onChange={e => setNewDesc(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Due Date & Time</label>
                  <input 
                    type="datetime-local" 
                    className="form-input" 
                    value={newDueDate}
                    onChange={e => setNewDueDate(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Total Time Budget (Optional Hours)</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    step="0.5"
                    placeholder="Leave empty for Gemini to estimate" 
                    value={newHours}
                    onChange={e => setNewHours(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Goal Category</label>
                <select 
                  className="form-input" 
                  value={newCategory}
                  onChange={e => setNewCategory(e.target.value)}
                >
                  <option value="study">Study / Exam prep</option>
                  <option value="work">Work project</option>
                  <option value="personal">Personal goal</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
                <button type="submit" className="btn btn-primary" disabled={formLoading}>
                  {formLoading ? '🤖 Decomposing Schedule...' : '🔮 Let AI Plan Schedule'}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setActiveTab('dashboard')}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* BIO SETTINGS TAB */}
        {activeTab === 'profile' && (
          <div className="glass-panel card" style={{ maxWidth: '700px', marginInline: 'auto' }}>
            <h3 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>Bio-Clock Productivity Settings</h3>
            <p style={{ color: 'hsl(var(--text-secondary))', marginBottom: '2rem' }}>
              Tailor the AI scheduler to your sleep cycles and peak productivity hours. When saved, all active schedules will be automatically shifted and reorganized.
            </p>

            <form onSubmit={handleProfileSave}>
              <div className="form-group">
                <label className="form-label">Display Name</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={profName}
                  onChange={e => setProfName(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Preferred Working Start (24h)</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="09:00"
                    value={profStart}
                    onChange={e => setProfStart(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Preferred Working End (24h)</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="18:00"
                    value={profEnd}
                    onChange={e => setProfEnd(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Circadian Energy Profile</label>
                <select 
                  className="form-input" 
                  value={profEnergy}
                  onChange={e => setProfEnergy(e.target.value)}
                >
                  <option value="consistent">Consistent throughout the day</option>
                  <option value="morning_person">Morning Peak (Early Bird)</option>
                  <option value="night_owl">Night Peak (Night Owl)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Stress Coping Style</label>
                <select 
                  className="form-input" 
                  value={profStress}
                  onChange={e => setProfStress(e.target.value)}
                >
                  <option value="break_into_tiny_steps">Break into tiny, micro-steps (Low Stress)</option>
                  <option value="deep_focus_blocks">Deep, continuous focus blocks (High Density)</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
                <button type="submit" className="btn btn-primary" disabled={profileLoading}>
                  {profileLoading ? 'Recalculating Schedules...' : 'Save Settings'}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setActiveTab('dashboard')}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

      </main>

      {/* PANIC TRIGGER MODAL */}
      {isPanicModalOpen && selectedDeadline && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ color: 'hsl(var(--accent))', fontSize: '1.6rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              🚨 Trigger Panic Mode Triage
            </h3>
            <p style={{ color: 'hsl(var(--text-secondary))', marginBottom: '1.5rem' }}>
              Did you lose track of time? Did a task take much longer? Gemini will cut down lower priority subtasks, condense your scope, and fit remaining deliverables in your remaining time.
            </p>

            <div className="form-group">
              <label className="form-label">Lost or Wasted Hours (Delay Amount)</label>
              <input 
                type="number" 
                className="form-input" 
                step="0.5"
                min="0.5"
                value={panicLostHours}
                onChange={e => setPanicLostHours(parseFloat(e.target.value) || 0)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">What happened? (Optional context for Gemini)</label>
              <textarea 
                className="form-input" 
                placeholder="e.g. I got stuck debugging database config errors / got distracted watching tutorial videos"
                value={panicReason}
                onChange={e => setPanicReason(e.target.value)}
                style={{ minHeight: '80px', resize: 'vertical' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
              <button 
                type="button" 
                className="btn btn-panic" 
                disabled={panicLoading}
                onClick={() => handlePanicTrigger()}
              >
                {panicLoading ? '⚡ AI Calibrating...' : '🚨 Rescue My Deadline'}
              </button>
              <button 
                type="button" 
                className="btn btn-secondary" 
                disabled={panicLoading}
                onClick={() => setIsPanicModalOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
