import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  Settings, 
  FileText, 
  CalendarCheck, 
  Inbox, 
  Send, 
  LogOut, 
  User, 
  Plus, 
  Play, 
  Check, 
  X, 
  Edit, 
  RefreshCw, 
  AlertTriangle, 
  Sparkles,
  Calendar,
  MapPin,
  Eye
} from 'lucide-react';
import { api } from './services/api';

// --- MAIN TYPES ---
type Tab = 'dashboard' | 'sources' | 'raw-items' | 'events' | 'submissions' | 'posts';

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [user, setUser] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  
  // Auth state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  // Common notifications
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  useEffect(() => {
    if (token) {
      api.getMe()
        .then(setUser)
        .catch(() => {
          handleLogout();
        });
    }
  }, [token]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    try {
      const data = await api.login(email, password);
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      showToast('Вхід успішний!', 'success');
    } catch (err: any) {
      setAuthError(err.message || 'Помилка авторизації. Перевірте дані.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    showToast('Ви вийшли з системи.', 'info');
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0b0f19] px-4 relative overflow-hidden">
        {/* Glow Effects */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[100px] animate-pulse-slow"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/10 rounded-full blur-[100px] animate-pulse-slow"></div>
        
        <div className="w-full max-w-md p-8 rounded-2xl glass-panel relative z-10 border border-slate-800 shadow-2xl">
          <div className="flex flex-col items-center mb-8">
            <span className="text-5xl mb-3">🎭</span>
            <h1 className="text-2xl font-bold tracking-tight text-white">Куди піти Київ</h1>
            <p className="text-sm text-muted mt-1 text-center">Вхід в панель керування агрегатором</p>
          </div>

          {authError && (
            <div className="mb-6 p-4 rounded-xl bg-danger/10 border border-danger/20 text-danger text-sm flex items-center gap-2">
              <AlertTriangle size={18} />
              <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Email Адреса</label>
              <input 
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="editor@kyivevents.com"
                className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-primary transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Пароль</label>
              <input 
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-primary transition"
              />
            </div>

            <button 
              type="submit"
              disabled={authLoading}
              className="w-full py-3.5 rounded-xl bg-gradient-to-r from-primary to-secondary text-white font-semibold glowing-btn hover:opacity-90 disabled:opacity-50 transition"
            >
              {authLoading ? 'Авторизація...' : 'Увійти'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070b13] flex relative">
      {/* Toast Alert */}
      {toast && (
        <div className={`fixed bottom-6 right-6 px-6 py-4 rounded-xl z-50 shadow-2xl border flex items-center gap-3 transition-all transform translate-y-0 ${
          toast.type === 'success' ? 'bg-success/15 border-success/30 text-success' :
          toast.type === 'error' ? 'bg-danger/15 border-danger/30 text-danger' : 'bg-primary/15 border-primary/30 text-primary'
        }`}>
          {toast.type === 'success' ? <Check size={20} /> : <AlertTriangle size={20} />}
          <span className="font-medium text-sm">{toast.message}</span>
        </div>
      )}

      {/* SIDEBAR */}
      <aside className="w-72 bg-card border-r border-slate-900 flex flex-col justify-between p-6">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-3 mb-8 px-2">
            <span className="text-3xl">🎭</span>
            <div>
              <h2 className="font-bold text-white text-base leading-tight">Куди піти Київ</h2>
              <span className="text-xs text-muted">Контроль подій v1.0</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5">
            <SidebarLink 
              icon={<LayoutDashboard size={20} />} 
              label="Дашборд" 
              active={activeTab === 'dashboard'} 
              onClick={() => setActiveTab('dashboard')} 
            />
            <SidebarLink 
              icon={<Settings size={20} />} 
              label="Джерела даних" 
              active={activeTab === 'sources'} 
              onClick={() => setActiveTab('sources')} 
            />
            <SidebarLink 
              icon={<FileText size={20} />} 
              label="Свіжі матеріали" 
              active={activeTab === 'raw-items'} 
              onClick={() => setActiveTab('raw-items')} 
            />
            <SidebarLink 
              icon={<CalendarCheck size={20} />} 
              label="Модерація подій" 
              active={activeTab === 'events'} 
              onClick={() => setActiveTab('events')} 
            />
            <SidebarLink 
              icon={<Inbox size={20} />} 
              label="Заявки боту" 
              active={activeTab === 'submissions'} 
              onClick={() => setActiveTab('submissions')} 
            />
            <SidebarLink 
              icon={<Send size={20} />} 
              label="Публікації" 
              active={activeTab === 'posts'} 
              onClick={() => setActiveTab('posts')} 
            />
          </nav>
        </div>

        {/* User Card & Logout */}
        <div className="border-t border-slate-800 pt-6">
          <div className="flex items-center gap-3 mb-4 px-2">
            <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-white border border-slate-700">
              <User size={18} />
            </div>
            <div className="overflow-hidden">
              <p className="text-sm font-semibold text-white truncate">{user?.email || 'Користувач'}</p>
              <span className="text-xs text-muted uppercase tracking-wider font-medium">{user?.role || 'редактор'}</span>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-900 transition text-sm font-medium"
          >
            <LogOut size={16} />
            <span>Вийти</span>
          </button>
        </div>
      </aside>

      {/* MAIN VIEW AREA */}
      <main className="flex-1 overflow-y-auto px-10 py-8">
        {activeTab === 'dashboard' && <DashboardView showToast={showToast} />}
        {activeTab === 'sources' && <SourcesView showToast={showToast} />}
        {activeTab === 'raw-items' && <RawItemsView showToast={showToast} />}
        {activeTab === 'events' && <EventsModerationView showToast={showToast} />}
        {activeTab === 'submissions' && <SubmissionsView showToast={showToast} />}
        {activeTab === 'posts' && <PostsView showToast={showToast} />}
      </main>
    </div>
  );
}

// --- SIDEBAR COMPONENT LINK ---
function SidebarLink({ icon, label, active, onClick }: { icon: React.ReactNode; label: string; active: boolean; onClick: () => void }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl transition text-sm font-medium ${
        active 
          ? 'bg-gradient-to-r from-primary/20 to-secondary/10 border border-primary/20 text-white' 
          : 'text-slate-400 hover:text-white hover:bg-slate-900/50 border border-transparent'
      }`}
    >
      <span className={active ? 'text-primary' : 'text-slate-400'}>{icon}</span>
      <span>{label}</span>
    </button>
  );
}

// --- 1. DASHBOARD VIEW ---
function DashboardView({ showToast }: { showToast: any }) {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const data = await api.getDashboardStats();
      setStats(data);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="text-slate-400 text-sm">Завантаження статистики...</div>;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Стан системи</h1>
          <p className="text-sm text-muted mt-1">Огляд черг, помилок та активних джерел</p>
        </div>
        <button 
          onClick={fetchStats}
          className="p-3 rounded-xl border border-slate-800 text-slate-300 hover:bg-slate-900 hover:text-white transition flex items-center gap-2 text-sm font-medium"
        >
          <RefreshCw size={16} />
          Оновити
        </button>
      </div>

      {/* Grid Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
        <StatsCard title="Джерела" value={stats?.active_sources_count || 0} label="активних джерел" color="primary" />
        <StatsCard title="Свіжий контент" value={stats?.new_raw_items_count || 0} label="raw items чекають AI" color="secondary" />
        <StatsCard title="Модерація" value={stats?.review_events_count || 0} label="подій у черзі перевірки" color="warning" />
        <StatsCard title="Публікації сьогодні" value={stats?.published_today_count || 0} label="постів опубліковано" color="success" />
        <StatsCard title="Помилки парсерів" value={stats?.parser_errors_count || 0} label="збоїв зафіксовано" color="danger" />
      </div>

      {/* Error Logs Table */}
      <div className="rounded-2xl border border-slate-800 bg-card p-6 shadow-xl">
        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <AlertTriangle className="text-danger" size={20} />
          Журнал останніх збоїв парсерів
        </h3>
        
        {(!stats?.recent_errors || stats.recent_errors.length === 0) ? (
          <p className="text-sm text-slate-500 py-4">Жодних критичних збоїв не зафіксовано. Все працює стабільно!</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Час</th>
                  <th className="py-3 px-4">Джерело</th>
                  <th className="py-3 px-4">Тип помилки</th>
                  <th className="py-3 px-4">Опис</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 text-sm text-slate-300">
                {stats.recent_errors.map((err: any) => (
                  <tr key={err.id} className="hover:bg-slate-900/40">
                    <td className="py-3 px-4 text-xs font-medium text-slate-400">
                      {new Date(err.created_at).toLocaleString('uk-UA')}
                    </td>
                    <td className="py-3 px-4 font-semibold text-white">{err.source_name}</td>
                    <td className="py-3 px-4"><span className="px-2.5 py-1 rounded-md bg-danger/10 text-danger text-xs font-semibold">{err.error_type}</span></td>
                    <td className="py-3 px-4 truncate max-w-xs" title={err.error_message}>{err.error_message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function StatsCard({ title, value, label, color }: { title: string; value: number; label: string; color: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' }) {
  const colorMap = {
    primary: 'border-l-primary text-primary',
    secondary: 'border-l-secondary text-secondary',
    success: 'border-l-success text-success',
    warning: 'border-l-warning text-warning',
    danger: 'border-l-danger text-danger',
  };
  return (
    <div className={`p-6 rounded-2xl bg-card border border-slate-800 border-l-4 ${colorMap[color]} shadow-lg`}>
      <p className="text-xs uppercase tracking-wider font-semibold text-slate-400">{title}</p>
      <h3 className="text-3xl font-extrabold text-white mt-2 tracking-tight">{value}</h3>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  );
}

// --- 2. SOURCES VIEW ---
function SourcesView({ showToast }: { showToast: any }) {
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingSource, setEditingSource] = useState<any | null>(null);

  // Form states
  const [name, setName] = useState('');
  const [type, setType] = useState('rss'); // rss, website, telegram
  const [url, setUrl] = useState('');
  const [tgUsername, setTgUsername] = useState('');
  const [crawlInterval, setCrawlInterval] = useState(60);

  useEffect(() => {
    fetchSources();
  }, []);

  const fetchSources = async () => {
    setLoading(true);
    try {
      const data = await api.getSources();
      setSources(data);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleAddOrEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name,
      type,
      url: type !== 'telegram' ? url : null,
      telegram_channel_username: type === 'telegram' ? tgUsername : null,
      crawl_interval_minutes: crawlInterval,
      enabled: editingSource ? editingSource.enabled : true,
    };

    try {
      if (editingSource) {
        await api.updateSource(editingSource.id, payload);
        showToast('Джерело оновлено!', 'success');
      } else {
        await api.createSource(payload);
        showToast('Джерело додано!', 'success');
      }
      setShowModal(false);
      resetForm();
      fetchSources();
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleEditClick = (source: any) => {
    setEditingSource(source);
    setName(source.name);
    setType(source.type);
    setUrl(source.url || '');
    setTgUsername(source.telegram_channel_username || '');
    setCrawlInterval(source.crawl_interval_minutes);
    setShowModal(true);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Ви впевнені, що хочете видалити це джерело?')) return;
    try {
      await api.deleteSource(id);
      showToast('Джерело видалено.', 'info');
      fetchSources();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleToggleEnable = async (source: any) => {
    try {
      await api.updateSource(source.id, { enabled: !source.enabled });
      showToast(source.enabled ? 'Джерело вимкнено' : 'Джерело увімкнено', 'info');
      fetchSources();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleCrawlNow = async (id: number) => {
    try {
      await api.crawlSource(id);
      showToast('Збір даних активовано в фоні.', 'success');
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const resetForm = () => {
    setEditingSource(null);
    setName('');
    setType('rss');
    setUrl('');
    setTgUsername('');
    setCrawlInterval(60);
  };

  if (loading) return <div className="text-slate-400 text-sm">Завантаження джерел...</div>;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Джерела подій</h1>
          <p className="text-sm text-muted mt-1 font-medium">Керування підключеними сайтами, RSS-афішами та TG-каналами</p>
        </div>
        <button 
          onClick={() => { resetForm(); setShowModal(true); }}
          className="px-5 py-3 rounded-xl bg-gradient-to-r from-primary to-secondary text-white font-semibold glowing-btn flex items-center gap-2 text-sm"
        >
          <Plus size={18} />
          Додати джерело
        </button>
      </div>

      {/* Sources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {sources.map((src) => (
          <div key={src.id} className="p-6 rounded-2xl bg-card border border-slate-800 shadow-xl hover:border-slate-700/60 transition flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-3">
                <span className={`px-3 py-1 rounded-md text-xs font-semibold uppercase tracking-wider ${
                  src.type === 'rss' ? 'bg-primary/10 text-primary' :
                  src.type === 'website' ? 'bg-secondary/10 text-secondary' : 'bg-success/10 text-success'
                }`}>
                  {src.type}
                </span>
                
                {/* Switch toggler */}
                <button 
                  onClick={() => handleToggleEnable(src)}
                  className={`w-11 h-6 rounded-full p-1 transition-colors flex ${
                    src.enabled ? 'bg-success justify-end' : 'bg-slate-800 justify-start'
                  }`}
                >
                  <span className="w-4 h-4 bg-white rounded-full"></span>
                </button>
              </div>

              <h3 className="text-lg font-bold text-white leading-tight">{src.name}</h3>
              <p className="text-xs text-slate-500 mt-2 truncate">
                {src.type === 'telegram' ? `@${src.telegram_channel_username}` : src.url}
              </p>
              
              <div className="mt-4 flex items-center gap-4 text-xs text-slate-400">
                <div>Перевірка: <span className="font-semibold">{src.crawl_interval_minutes} хв</span></div>
                {src.last_checked_at && (
                  <div>Скановано: <span className="font-semibold">{new Date(src.last_checked_at).toLocaleTimeString('uk-UA')}</span></div>
                )}
              </div>
            </div>

            <div className="mt-6 border-t border-slate-800/80 pt-4 flex gap-2">
              <button 
                onClick={() => handleCrawlNow(src.id)}
                disabled={!src.enabled}
                className="flex-1 py-2 px-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-50 text-xs font-semibold flex items-center justify-center gap-1.5 transition"
              >
                <Play size={12} /> Запустити
              </button>
              
              <button 
                onClick={() => handleEditClick(src)}
                className="py-2 px-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 text-xs font-semibold flex items-center justify-center gap-1.5 transition"
              >
                <Edit size={12} /> Редагувати
              </button>

              <button 
                onClick={() => handleDelete(src.id)}
                className="py-2 px-3 rounded-lg bg-danger/10 border border-danger/20 text-danger hover:bg-danger/25 text-xs font-semibold flex items-center justify-center gap-1.5 transition"
              >
                Видалити
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* CRUD MODAL */}
      {showModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg p-8 rounded-2xl bg-card border border-slate-800 shadow-2xl relative">
            <button 
              onClick={() => setShowModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition"
            >
              <X size={20} />
            </button>
            
            <h2 className="text-xl font-bold text-white mb-6">
              {editingSource ? 'Редагувати джерело' : 'Додати нове джерело'}
            </h2>
            
            <form onSubmit={handleAddOrEdit} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Назва Джерела</label>
                <input 
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Concert.ua Київ"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-primary transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Тип</label>
                <select 
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white focus:outline-none focus:border-primary transition"
                >
                  <option value="rss">RSS Стрічка</option>
                  <option value="website">Веб-сайт</option>
                  <option value="telegram">Telegram канал</option>
                </select>
              </div>

              {type !== 'telegram' ? (
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">URL Адреса</label>
                  <input 
                    type="url"
                    required
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://concert.ua/uk/kyiv"
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-primary transition"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Telegram Username Каналу</label>
                  <input 
                    type="text"
                    required
                    value={tgUsername}
                    onChange={(e) => setTgUsername(e.target.value)}
                    placeholder="kyiv_afisha"
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-primary transition"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Інтервал перевірки (хвилини)</label>
                <input 
                  type="number"
                  required
                  min="5"
                  value={crawlInterval}
                  onChange={(e) => setCrawlInterval(parseInt(e.target.value))}
                  placeholder="60"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-primary transition"
                />
              </div>

              <div className="pt-4 flex gap-3">
                <button 
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-3 rounded-xl border border-slate-800 text-slate-300 hover:bg-slate-900 transition font-medium"
                >
                  Скасувати
                </button>
                <button 
                  type="submit"
                  className="flex-1 py-3 rounded-xl bg-gradient-to-r from-primary to-secondary text-white font-semibold glowing-btn"
                >
                  {editingSource ? 'Зберегти зміни' : 'Створити'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// --- 3. RAW ITEMS VIEW ---
function RawItemsView({ showToast }: { showToast: any }) {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [viewItem, setViewItem] = useState<any | null>(null);

  useEffect(() => {
    fetchRawItems();
  }, [statusFilter]);

  const fetchRawItems = async () => {
    setLoading(true);
    try {
      const data = await api.getRawItems(statusFilter || undefined);
      setItems(data);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReprocess = async (id: number) => {
    try {
      await api.reprocessRawItem(id);
      showToast('Reprocess triggered! Check Events list shortly.', 'success');
      setViewItem(null);
      fetchRawItems();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Свіжі матеріали (Raw Items)</h1>
          <p className="text-sm text-muted mt-1 font-medium">Список сирих даних, які було імпортовано краулером</p>
        </div>

        {/* Filter select */}
        <select 
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2.5 rounded-xl bg-card border border-slate-800 text-white focus:outline-none focus:border-primary text-sm font-semibold transition"
        >
          <option value="">Усі статуси</option>
          <option value="new">Нові (New)</option>
          <option value="processed">Оброблено AI</option>
          <option value="ignored">Проігноровано AI</option>
          <option value="error">Помилка AI</option>
        </select>
      </div>

      {loading ? (
        <div className="text-slate-400 text-sm">Завантаження матеріалів...</div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-card p-12 text-center text-slate-500">
          Матеріали не знайдені. Спробуйте запустити краулер вручну у розділі Джерела.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {items.map((item) => (
            <div 
              key={item.id}
              className="p-5 rounded-2xl bg-card border border-slate-800 flex justify-between items-center hover:border-slate-700/60 transition cursor-pointer"
              onClick={() => setViewItem(item)}
            >
              <div className="overflow-hidden pr-6">
                <div className="flex items-center gap-3 mb-2">
                  <span className={`px-2.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                    item.processing_status === 'new' ? 'bg-primary/10 text-primary' :
                    item.processing_status === 'processed' ? 'bg-success/10 text-success' :
                    item.processing_status === 'ignored' ? 'bg-slate-700/40 text-slate-400' : 'bg-danger/10 text-danger'
                  }`}>
                    {item.processing_status}
                  </span>
                  <span className="text-[11px] text-slate-500">{new Date(item.fetched_at).toLocaleString('uk-UA')}</span>
                </div>
                <h3 className="font-semibold text-white truncate text-base">{item.title || 'Подія без назви'}</h3>
                <p className="text-xs text-slate-500 mt-1 truncate">{item.url || 'Джерело без посилання'}</p>
              </div>

              <button className="p-3.5 rounded-xl border border-slate-800 text-slate-300 hover:bg-slate-900 transition flex items-center gap-2 text-xs font-semibold shrink-0">
                <Eye size={14} /> Перегляд
              </button>
            </div>
          ))}
        </div>
      )}

      {/* VIEW MODAL */}
      {viewItem && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-3xl p-8 rounded-2xl bg-card border border-slate-800 shadow-2xl relative max-h-[85vh] overflow-y-auto">
            <button 
              onClick={() => setViewItem(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition"
            >
              <X size={20} />
            </button>
            
            <h2 className="text-xl font-bold text-white mb-2">{viewItem.title || 'Пост без заголовку'}</h2>
            <p className="text-xs text-muted mb-6">Отримано {new Date(viewItem.fetched_at).toLocaleString('uk-UA')} · URL: <a href={viewItem.url} target="_blank" rel="noreferrer" className="text-primary hover:underline">{viewItem.url || 'немає'}</a></p>

            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 mb-6 text-sm text-slate-300 leading-relaxed font-sans whitespace-pre-wrap max-h-72 overflow-y-auto">
              {viewItem.raw_text}
            </div>

            {viewItem.error_message && (
              <div className="mb-6 p-4 rounded-xl bg-danger/10 border border-danger/20 text-danger text-sm">
                <p className="font-semibold flex items-center gap-2 mb-2"><AlertTriangle size={16} /> Помилка обробки AI:</p>
                <pre className="text-xs font-mono whitespace-pre-wrap leading-tight max-h-40 overflow-y-auto bg-slate-950/60 p-3 rounded-lg">{viewItem.error_message}</pre>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <button 
                onClick={() => setViewItem(null)}
                className="py-3 px-6 rounded-xl border border-slate-800 text-slate-300 hover:bg-slate-900 transition text-sm font-medium"
              >
                Закрити
              </button>
              
              <button 
                onClick={() => handleReprocess(viewItem.id)}
                className="py-3 px-6 rounded-xl bg-gradient-to-r from-primary to-secondary text-white font-semibold glowing-btn text-sm flex items-center gap-2"
              >
                <Sparkles size={16} />
                Обробити AI повторно
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// --- 4. EVENTS MODERATION VIEW (SPLIT SCREEN) ---
function EventsModerationView({ showToast }: { showToast: any }) {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('needs_review'); // default show needs review
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null);

  // Edit details form states
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('');
  const [dateText, setDateText] = useState('');
  const [startDateTime, setStartDateTime] = useState('');
  const [venue, setVenue] = useState('');
  const [address, setAddress] = useState('');
  const [priceText, setPriceText] = useState('');
  const [priceMin, setPriceMin] = useState<number | ''>('');
  const [priceMax, setPriceMax] = useState<number | ''>('');
  const [isFree, setIsFree] = useState(false);
  const [ticketUrl, setTicketUrl] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [descriptionCard, setDescriptionCard] = useState(''); // editable right side text
  
  // Schedule state
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleTime, setScheduleTime] = useState('');

  // Duplicates state
  const [duplicates, setDuplicates] = useState<any[]>([]);
  const [dupsLoading, setDupsLoading] = useState(false);

  useEffect(() => {
    fetchEvents();
  }, [statusFilter]);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const data = await api.getEvents(statusFilter || undefined);
      setEvents(data);
      if (selectedEvent) {
        // Clear selection to prevent stale edits
        setSelectedEvent(null);
      }
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectEvent = async (event: any) => {
    setSelectedEvent(event);
    setTitle(event.title || '');
    setCategory(event.category || 'other');
    setDateText(event.date_text_original || '');
    setStartDateTime(event.start_datetime ? event.start_datetime.substring(0, 16) : '');
    setVenue(event.venue_name || '');
    setAddress(event.address || '');
    setPriceText(event.price_text_original || '');
    setPriceMin(event.price_min !== null ? parseFloat(event.price_min) : '');
    setPriceMax(event.price_max !== null ? parseFloat(event.price_max) : '');
    setIsFree(event.is_free || false);
    setTicketUrl(event.ticket_url || '');
    setImageUrl(event.image_url || '');
    setDescriptionCard(event.short_description || '');

    // Fetch potential duplicates
    setDupsLoading(true);
    setDuplicates([]);
    try {
      const dupData = await api.getPossibleDuplicates(event.id);
      setDuplicates(dupData);
    } catch (e: any) {
      console.error('Failed to fetch duplicates', e);
    } finally {
      setDupsLoading(false);
    }
  };

  const handleSaveChanges = async () => {
    if (!selectedEvent) return;
    const payload = {
      title,
      category,
      date_text_original: dateText,
      start_datetime: startDateTime ? new Date(startDateTime).toISOString() : null,
      venue_name: venue,
      address,
      price_text_original: priceText,
      price_min: priceMin !== '' ? priceMin : null,
      price_max: priceMax !== '' ? priceMax : null,
      is_free: isFree,
      ticket_url: ticketUrl,
      image_url: imageUrl,
      short_description: descriptionCard,
    };
    try {
      const updated = await api.updateEvent(selectedEvent.id, payload);
      showToast('Зміни збережено!', 'success');
      // Refresh current event
      setSelectedEvent(updated);
      // Refresh list
      fetchEvents();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await api.approveEvent(id);
      showToast('Подія схвалена!', 'success');
      fetchEvents();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleReject = async (id: number) => {
    try {
      await api.rejectEvent(id);
      showToast('Подію відхилено.', 'info');
      fetchEvents();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handlePublishNow = async (id: number) => {
    // Save current changes first
    await handleSaveChanges();
    try {
      await api.publishEvent(id);
      showToast('Подія успішно опублікована в Telegram-каналі!', 'success');
      fetchEvents();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleScheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEvent || !scheduleTime) return;
    try {
      await api.scheduleEvent(selectedEvent.id, new Date(scheduleTime).toISOString());
      showToast(`Подію заплановано до публікації!`, 'success');
      setShowScheduleModal(false);
      fetchEvents();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleRegenerateText = async () => {
    if (!selectedEvent) return;
    try {
      const res = await api.regenerateEventText(selectedEvent.id);
      setDescriptionCard(res.short_description);
      showToast('AI опис успішно перегенеровано!', 'success');
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleMergeDuplicate = async (dupId: number) => {
    if (!selectedEvent) return;
    if (!window.confirm('Ви впевнені, що хочете об\'єднати ці події? Ця дія rejected дублікат та згрупує їх.')) return;
    try {
      await api.mergeDuplicate(dupId, selectedEvent.id);
      showToast('Події об\'єднано успішно!', 'success');
      // Re-fetch duplicates
      const dupData = await api.getPossibleDuplicates(selectedEvent.id);
      setDuplicates(dupData);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Модерація подій</h1>
          <p className="text-sm text-muted mt-1 font-medium">Підтвердження, редагування, склеювання дублів та публікація у канал</p>
        </div>

        {/* Filter select */}
        <select 
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2.5 rounded-xl bg-card border border-slate-800 text-white focus:outline-none focus:border-primary text-sm font-semibold transition"
        >
          <option value="needs_review">Потрібен огляд (Needs Review)</option>
          <option value="draft">Чернетки (Draft)</option>
          <option value="approved">Схвалені (Approved)</option>
          <option value="published">Опубліковані (Published)</option>
          <option value="rejected">Відхилені (Rejected)</option>
          <option value="archived">Архівні (Archived)</option>
        </select>
      </div>

      <div className="flex gap-8 relative items-start">
        {/* LEFT COLUMN: LIST of events */}
        <div className={`w-80 space-y-4 max-h-[75vh] overflow-y-auto shrink-0 transition-all ${
          selectedEvent ? 'hidden md:block' : 'w-full'
        }`}>
          {loading ? (
            <div className="text-slate-400 text-sm">Завантаження черги...</div>
          ) : events.length === 0 ? (
            <div className="rounded-2xl border border-slate-800 bg-card p-12 text-center text-slate-500">
              Подій із цим статусом немає.
            </div>
          ) : (
            events.map((ev) => (
              <div 
                key={ev.id}
                onClick={() => handleSelectEvent(ev)}
                className={`p-4 rounded-xl border transition cursor-pointer text-left ${
                  selectedEvent?.id === ev.id 
                    ? 'bg-gradient-to-r from-primary/10 to-transparent border-primary' 
                    : 'bg-card border-slate-800 hover:border-slate-700/60'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] uppercase font-bold tracking-wider">{ev.category || 'інше'}</span>
                  {ev.quality_score !== null && (
                    <span className={`text-[10px] font-bold ${
                      ev.quality_score >= 70 ? 'text-success' :
                      ev.quality_score >= 50 ? 'text-warning' : 'text-danger'
                    }`}>
                      QS: {ev.quality_score}%
                    </span>
                  )}
                </div>
                <h4 className="font-semibold text-white text-sm truncate">{ev.title}</h4>
                <p className="text-xs text-slate-500 mt-1 flex items-center gap-1.5 truncate">
                  <MapPin size={12} /> {ev.venue_name || 'Уточнюється'}
                </p>
                <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1.5">
                  <Calendar size={12} /> {ev.date_text_original || 'Невідомо'}
                </p>
              </div>
            ))
          )}
        </div>

        {/* RIGHT COLUMN: EVENT DETAIL & PREVIEW SPLIT SCREEN */}
        {selectedEvent ? (
          <div className="flex-1 grid grid-cols-1 xl:grid-cols-2 gap-8 bg-[#0b101c] border border-slate-800/80 rounded-2xl p-6 shadow-2xl relative">
            <button 
              onClick={() => setSelectedEvent(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white md:hidden"
            >
              <X size={20} />
            </button>

            {/* LEFT SPLIT: Form Editor */}
            <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-4 text-left">
              <h3 className="text-lg font-bold text-white mb-2">Редактор події</h3>
              
              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Заголовок</label>
                <input 
                  type="text" 
                  value={title} 
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white focus:outline-none focus:border-primary transition"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Категорія</label>
                  <select 
                    value={category} 
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white focus:outline-none"
                  >
                    <option value="today">Сьогодні</option>
                    <option value="weekend">Вихідні</option>
                    <option value="concert">Концерти</option>
                    <option value="theater">Театр</option>
                    <option value="standup">Стендап</option>
                    <option value="exhibition">Виставки</option>
                    <option value="party">Вечірки</option>
                    <option value="food">Їжа</option>
                    <option value="bar">Бари</option>
                    <option value="kids">Дітям</option>
                    <option value="family">Сімейні</option>
                    <option value="date">Побачення</option>
                    <option value="free">Безкоштовно</option>
                    <option value="other">Інше</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Оригінальна дата</label>
                  <input 
                    type="text" 
                    value={dateText} 
                    onChange={(e) => setDateText(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Нормалізована Дата та Час</label>
                <input 
                  type="datetime-local" 
                  value={startDateTime} 
                  onChange={(e) => setStartDateTime(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Локація (Місце)</label>
                  <input 
                    type="text" 
                    value={venue} 
                    onChange={(e) => setVenue(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Адреса</label>
                  <input 
                    type="text" 
                    value={address} 
                    onChange={(e) => setAddress(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Оригінальна ціна</label>
                  <input 
                    type="text" 
                    value={priceText} 
                    onChange={(e) => setPriceText(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white focus:outline-none"
                  />
                </div>
                <div className="flex items-center pt-5 pl-2">
                  <label className="flex items-center gap-2 text-xs font-semibold text-slate-300 select-none cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={isFree} 
                      onChange={(e) => setIsFree(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-800 text-primary focus:ring-0" 
                    />
                    <span>Безкоштовно</span>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Ціна від (грн)</label>
                  <input 
                    type="number" 
                    value={priceMin} 
                    onChange={(e) => setPriceMin(e.target.value !== '' ? parseInt(e.target.value) : '')}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Ціна до (грн)</label>
                  <input 
                    type="number" 
                    value={priceMax} 
                    onChange={(e) => setPriceMax(e.target.value !== '' ? parseInt(e.target.value) : '')}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Посилання (квитки)</label>
                <input 
                  type="text" 
                  value={ticketUrl} 
                  onChange={(e) => setTicketUrl(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Посилання на картинку</label>
                <input 
                  type="text" 
                  value={imageUrl} 
                  onChange={(e) => setImageUrl(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white"
                />
              </div>

              <div className="pt-2">
                <button 
                  onClick={handleSaveChanges}
                  className="py-2.5 px-4 rounded-xl border border-primary/20 text-primary bg-primary/5 hover:bg-primary/10 transition text-xs font-bold w-full"
                >
                  Зберегти зміни в редакторі
                </button>
              </div>

              {/* Duplicate List section */}
              <div className="mt-6 border-t border-slate-850 pt-4">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Потенційні дублікати події</h4>
                {dupsLoading ? (
                  <span className="text-xs text-slate-500">Пошук схожих подій...</span>
                ) : duplicates.length === 0 ? (
                  <span className="text-xs text-slate-500">Дублікатів не знайдено в межах ±3 днів.</span>
                ) : (
                  <div className="space-y-2">
                    {duplicates.map((dup) => (
                      <div key={dup.id} className="p-3 bg-slate-900 border border-slate-800/80 rounded-lg flex items-center justify-between">
                        <div className="overflow-hidden pr-2">
                          <p className="text-xs text-white font-semibold truncate">{dup.title}</p>
                          <span className="text-[10px] text-slate-500">{dup.venue_name} · {dup.date_text_original}</span>
                        </div>
                        <button 
                          onClick={() => handleMergeDuplicate(dup.id)}
                          className="px-2.5 py-1 rounded bg-secondary/15 text-secondary border border-secondary/20 hover:bg-secondary/25 text-[10px] font-bold shrink-0 transition"
                        >
                          Склеїти
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* RIGHT SPLIT: Telegram Channel Post Preview */}
            <div className="flex flex-col justify-between max-h-[70vh] overflow-y-auto pl-4 border-t xl:border-t-0 xl:border-l border-slate-850 pt-6 xl:pt-0">
              <div className="text-left space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-bold text-white">Перегляд в Telegram</h3>
                  <button 
                    onClick={handleRegenerateText}
                    className="p-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-white transition flex items-center gap-1 text-[10px] font-bold"
                    title="Запустити AI для переписування картки"
                  >
                    <Sparkles size={12} /> AI Rewrite
                  </button>
                </div>

                {/* Simulated Telegram Message bubble */}
                <div className="rounded-xl bg-slate-900 border border-slate-850/60 p-4 max-w-sm mx-auto shadow-2xl relative">
                  {imageUrl && (
                    <img 
                      src={imageUrl} 
                      alt="Afisha Preview" 
                      className="w-full h-44 object-cover rounded-lg mb-3 border border-slate-850"
                      onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                    />
                  )}
                  
                  {/* Card content preview */}
                  <div className="text-sm font-sans text-slate-200 leading-relaxed whitespace-pre-wrap">
                    🎭 **{title}**<br/><br/>
                    📅 **Коли:** {dateText || 'не вказано'}<br/>
                    📍 **Де:** {venue}{address ? `, ${address}` : ''}<br/>
                    💸 **Ціна:** {isFree ? 'Безкоштовно' : priceText || 'уточнюється'}<br/>
                    👥 **Підійде для:** {category === 'date' ? 'побачення' : category === 'kids' ? 'сімейного відпочинку' : 'цікавого дозвілля'}<br/><br/>
                    ⭐ **Чому варто піти:**<br/>
                    {descriptionCard || 'Опис переписується штучним інтелектом...'}
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-850 text-[10px] text-slate-500 font-semibold uppercase tracking-wider flex justify-between">
                    <span>Канал: @KyivAfisha</span>
                    <span>Джерело: {selectedEvent.source_name || 'manual'}</span>
                  </div>
                </div>

                {/* Edit short description text card */}
                <div className="mt-4">
                  <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Опис для Telegram (редагування тексту)</label>
                  <textarea 
                    value={descriptionCard}
                    onChange={(e) => setDescriptionCard(e.target.value)}
                    rows={4}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-900 border border-slate-800 text-white focus:outline-none focus:border-primary font-sans leading-relaxed transition"
                  />
                </div>
              </div>

              {/* Action buttons */}
              <div className="pt-6 border-t border-slate-850 flex gap-2">
                <button 
                  onClick={() => handleReject(selectedEvent.id)}
                  className="flex-1 py-3 rounded-xl border border-danger/20 text-danger bg-danger/5 hover:bg-danger/10 transition text-xs font-bold"
                >
                  Відхилити
                </button>
                <button 
                  onClick={() => handleApprove(selectedEvent.id)}
                  className="flex-1 py-3 rounded-xl border border-slate-800 text-slate-300 hover:bg-slate-900 transition text-xs font-bold"
                >
                  Схвалити
                </button>
                <button 
                  onClick={() => setShowScheduleModal(true)}
                  className="flex-1 py-3 rounded-xl border border-primary/20 text-primary bg-primary/5 hover:bg-primary/10 transition text-xs font-bold"
                >
                  Розклад
                </button>
                <button 
                  onClick={() => handlePublishNow(selectedEvent.id)}
                  className="flex-1 py-3 rounded-xl bg-gradient-to-r from-primary to-secondary text-white font-semibold glowing-btn text-xs"
                >
                  Публікувати
                </button>
              </div>
            </div>

            {/* SCHEDULE TIMER DIALOG */}
            {showScheduleModal && (
              <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                <div className="w-full max-w-sm p-6 rounded-2xl bg-card border border-slate-800 shadow-2xl relative text-left">
                  <button 
                    onClick={() => setShowScheduleModal(false)}
                    className="absolute top-4 right-4 text-slate-400 hover:text-white transition"
                  >
                    <X size={20} />
                  </button>
                  <h3 className="text-lg font-bold text-white mb-4">Розклад публікації</h3>
                  <form onSubmit={handleScheduleSubmit} className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Оберіть дату та час</label>
                      <input 
                        type="datetime-local" 
                        required
                        value={scheduleTime}
                        onChange={(e) => setScheduleTime(e.target.value)}
                        className="w-full px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-white"
                      />
                    </div>
                    <button 
                      type="submit"
                      className="w-full py-3 rounded-xl bg-primary text-white font-semibold glowing-btn text-sm"
                    >
                      Запланувати
                    </button>
                  </form>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 rounded-2xl border border-dashed border-slate-800 p-24 text-center text-slate-500 font-medium h-[50vh] flex flex-col items-center justify-center gap-3">
            <Eye size={40} className="text-slate-700 animate-pulse" />
            <span>Оберіть подію з черги ліворуч для перегляду та модерації</span>
          </div>
        )}
      </div>
    </div>
  );
}

// --- 5. SUBMISSIONS VIEW ---
function SubmissionsView({ showToast }: { showToast: any }) {
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSubmissions();
  }, []);

  const fetchSubmissions = async () => {
    setLoading(true);
    try {
      const data = await api.getSubmissions('new'); // only get new submissions
      setSubmissions(data);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async (id: number) => {
    try {
      await api.acceptSubmission(id);
      showToast('Заявку прийнято та створено чернетку події!', 'success');
      fetchSubmissions();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleReject = async (id: number) => {
    try {
      await api.rejectSubmission(id);
      showToast('Заявку відхилено.', 'info');
      fetchSubmissions();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  if (loading) return <div className="text-slate-400 text-sm">Завантаження заявок...</div>;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Ручні заявки від організаторів</h1>
        <p className="text-sm text-muted mt-1 font-medium">Події, додані користувачами через Telegram-бота</p>
      </div>

      {submissions.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-card p-12 text-center text-slate-500">
          Нових заявок на модерацію немає.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-left">
          {submissions.map((sub) => (
            <div key={sub.id} className="p-6 rounded-2xl bg-card border border-slate-800 shadow-xl flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start mb-3">
                  <span className="text-[10px] text-slate-500 font-semibold">{new Date(sub.created_at).toLocaleString('uk-UA')}</span>
                  <span className="text-[11px] text-primary font-semibold">від @{sub.username || sub.user_id}</span>
                </div>
                <h3 className="text-lg font-bold text-white leading-tight">{sub.title}</h3>
                
                <div className="mt-4 space-y-2 text-sm text-slate-300 leading-relaxed font-sans whitespace-pre-wrap max-h-32 overflow-y-auto bg-slate-900/40 p-3 rounded-lg border border-slate-850">
                  {sub.description}
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-slate-400">
                  <div>Дата: <span className="font-semibold text-white">{sub.date_text}</span></div>
                  <div>Місце: <span className="font-semibold text-white">{sub.venue || 'уточнюється'}</span></div>
                  <div>Ціна: <span className="font-semibold text-white">{sub.price_text || 'безкоштовно'}</span></div>
                  {sub.link && (
                    <div className="truncate col-span-2">Посилання: <a href={sub.link} target="_blank" rel="noreferrer" className="text-primary hover:underline">{sub.link}</a></div>
                  )}
                </div>
              </div>

              <div className="mt-6 border-t border-slate-850 pt-4 flex gap-2">
                <button 
                  onClick={() => handleReject(sub.id)}
                  className="flex-1 py-2 rounded-lg bg-danger/10 border border-danger/20 text-danger hover:bg-danger/25 text-xs font-bold transition"
                >
                  Відхилити
                </button>
                <button 
                  onClick={() => handleAccept(sub.id)}
                  className="flex-1 py-2 rounded-lg bg-gradient-to-r from-primary to-secondary text-white font-bold glowing-btn text-xs flex items-center justify-center gap-1.5"
                >
                  Прийняти та Редагувати
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- 6. POSTS LOGS VIEW ---
function PostsView({ showToast }: { showToast: any }) {
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter] = useState('');

  useEffect(() => {
    fetchPosts();
  }, [typeFilter]);

  const fetchPosts = async () => {
    setLoading(true);
    try {
      const data = await api.getPosts(undefined, typeFilter || undefined);
      setPosts(data);
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handlePostDigest = async (type: 'daily' | 'tomorrow' | 'weekend') => {
    try {
      if (type === 'daily') {
        await api.triggerDailyDigest();
        showToast('Щоденна підбірка опублікована!', 'success');
      } else if (type === 'tomorrow') {
        await api.triggerTomorrowDigest();
        showToast('Підбірка на завтра опублікована!', 'success');
      } else {
        await api.triggerWeekendDigest();
        showToast('Підбірка вихідного дня опублікована!', 'success');
      }
      fetchPosts();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Журнал публікацій в Telegram</h1>
          <p className="text-sm text-muted mt-1 font-medium">Список постів, що відправлені на Telegram канал або заплановані</p>
        </div>

        <div className="flex gap-2">
          <button 
            onClick={() => handlePostDigest('daily')}
            className="px-4 py-2.5 rounded-xl border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-900 transition text-xs font-semibold"
          >
            Згенерувати дайджест "Сьогодні"
          </button>
          <button 
            onClick={() => handlePostDigest('tomorrow')}
            className="px-4 py-2.5 rounded-xl border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-900 transition text-xs font-semibold"
          >
            Згенерувати дайджест "Завтра"
          </button>
          <button 
            onClick={() => handlePostDigest('weekend')}
            className="px-4 py-2.5 rounded-xl border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-900 transition text-xs font-semibold"
          >
            Згенерувати дайджест "Вихідні"
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-slate-400 text-sm">Завантаження журналу...</div>
      ) : posts.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-card p-12 text-center text-slate-500">
          Публікацій не знайдено.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-card p-6 shadow-xl text-left">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Коли</th>
                <th className="py-3 px-4">Тип</th>
                <th className="py-3 px-4">Статус</th>
                <th className="py-3 px-4">Повідомлення в каналі (Текст)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-sm text-slate-300">
              {posts.map((post) => (
                <tr key={post.id} className="hover:bg-slate-900/40">
                  <td className="py-4 px-4 text-xs font-medium text-slate-400">
                    {new Date(post.scheduled_at).toLocaleString('uk-UA')}
                  </td>
                  <td className="py-4 px-4 font-semibold text-white">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                      post.post_type === 'single_event' ? 'bg-primary/10 text-primary' : 'bg-secondary/10 text-secondary'
                    }`}>
                      {post.post_type}
                    </span>
                  </td>
                  <td className="py-4 px-4">
                    <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${
                      post.status === 'published' ? 'bg-success/10 text-success' :
                      post.status === 'scheduled' ? 'bg-warning/10 text-warning' : 'bg-danger/10 text-danger'
                    }`}>
                      {post.status}
                    </span>
                  </td>
                  <td className="py-4 px-4 max-w-md truncate whitespace-pre-line text-xs leading-normal font-sans" title={post.text}>
                    {post.text}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
