'use strict';
/*
 * ZJCSAutoScript 配置界面。不依赖任何库：
 * - h() 建 DOM，属性或子节点传函数就是「动态的」，每次 refresh() 重新求值；
 * - 状态都在 S 里，改完调用 refresh()；保存时 POST /api/config，由 gui.py 校验后写回 config/zjcs.yaml。
 */
(() => {
  // ---------- DOM 小工具 ----------
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const ICONS = {
    route: '<circle cx="5.5" cy="5" r="2"/><circle cx="18.5" cy="19" r="2"/><path d="M8 5h6a3.5 3.5 0 0 1 0 7h-4a3.5 3.5 0 0 0 0 7h6"/>',
    chev: '<path d="M6 9l6 6 6-6"/>',
    minus: '<path d="M5 12h14"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    check: '<path d="M5 12l4 4 10-10"/>',
    shield: '<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    device: '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>',
    ban: '<circle cx="12" cy="12" r="9"/><path d="M6.5 6.5l11 11"/>',
    alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5M12 16.5v.5"/>',
    box: '<path d="M4 8l8-4 8 4v8l-8 4-8-4z"/><path d="M4 8l8 4 8-4M12 12v8"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>',
    moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4 7.5 7.5 0 1 0 20 14.5z"/>',
    monitor: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    activity: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
    tool: '<path d="M14.5 5.5a4 4 0 0 0 4.9 4.9L21 12l-9 9-3-3 9-9-1.6-1.6a4 4 0 0 0-4.9-4.9z" transform="translate(-2 -1)"/>',
    file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M4.2 7l2.6 1.5M17.2 15.5l2.6 1.5M4.2 17l2.6-1.5M17.2 8.5l2.6-1.5"/><circle cx="12" cy="12" r="7"/>',
    play: '<path d="M8 5.5v13l10.5-6.5z"/>',
    stop: '<rect x="6.5" y="6.5" width="11" height="11" rx="2"/>',
    bell: '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
    refresh: '<path d="M20 11a8 8 0 0 0-14.5-4.5L4 8M4 4v4h4M4 13a8 8 0 0 0 14.5 4.5L20 16M20 20v-4h-4"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    down: '<path d="M12 5v14M6 13l6 6 6-6"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    dock: '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M15 4v16"/><path d="M17.5 8.5h1M17.5 11h1"/>',
    expand: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
    max: '<rect x="5.5" y="5.5" width="13" height="13" rx="1.5"/>',
    min: '<path d="M5 12h14"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.6h.01"/>',
    inbox: '<path d="M3 13.5l2.6-7.2A2 2 0 0 1 7.5 5h9a2 2 0 0 1 1.9 1.3l2.6 7.2V18a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 13.5h5l1.5 2.5h5l1.5-2.5h5"/>',
    logs: '<rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M8 8.5h.01M11 8.5h5M8 12h.01M11 12h5M8 15.5h.01M11 15.5h5"/>',
    keyboard: '<rect x="2.5" y="6" width="19" height="12" rx="2"/><path d="M6 9.5h.01M9.5 9.5h.01M13 9.5h.01M16.5 9.5h.01M7 14.5h10"/>',
  };
  // 实心图标（运行按钮用）
  const FILLED = {
    play: '<path d="M7.5 5.2v13.6a.8.8 0 0 0 1.2.7l11-6.8a.8.8 0 0 0 0-1.4l-11-6.8a.8.8 0 0 0-1.2.7z"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2.2"/>',
  };
  const bindings = [];

  function icon(name, size = 18, cls = '') {
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('width', size);
    svg.setAttribute('height', size);
    svg.setAttribute('aria-hidden', 'true');
    if (cls) svg.setAttribute('class', cls);
    if (name === 'diamond') {
      svg.setAttribute('viewBox', '0 0 16 16');
      svg.innerHTML = '<path d="M8 1 15 8 8 15 1 8Z" fill="currentColor"/>';
    } else if (FILLED[name]) {
      svg.setAttribute('viewBox', '0 0 24 24');
      svg.setAttribute('fill', 'currentColor');
      svg.innerHTML = FILLED[name];
    } else {
      svg.setAttribute('viewBox', '0 0 24 24');
      svg.setAttribute('fill', 'none');
      svg.setAttribute('stroke', 'currentColor');
      svg.setAttribute('stroke-width', name === 'minus' || name === 'plus' || name === 'check' ? '2.2' : '1.8');
      svg.setAttribute('stroke-linecap', 'round');
      svg.setAttribute('stroke-linejoin', 'round');
      svg.innerHTML = ICONS[name];
    }
    return svg;
  }

  function applyProp(el, key, value) {
    if (key === 'class') {
      if (el.getAttribute('class') !== value) el.setAttribute('class', value);
    } else if (key === 'text') {
      const s = String(value);
      if (el.textContent !== s) el.textContent = s;
    } else if (key === 'show') {
      el.hidden = !value;
    } else if (key === 'inert') {
      el.inert = !!value;
    } else if (key === 'value') {
      // 正在输入的框不去改它，免得光标跳
      if (document.activeElement !== el && el.value !== String(value)) el.value = value;
    } else if (key === 'style') {
      Object.entries(value).forEach(([p, v]) => el.style.setProperty(p, v));
    } else if (value === null || value === undefined || value === false) {
      el.removeAttribute(key);
    } else {
      const s = value === true ? '' : String(value);
      if (el.getAttribute(key) !== s) el.setAttribute(key, s);
    }
  }

  function append(el, children) {
    children.flat(Infinity).forEach((c) => {
      if (c === null || c === undefined || c === false) return;
      if (typeof c === 'function') {
        const t = document.createTextNode(String(c()));
        bindings.push(() => {
          const s = String(c());
          if (t.data !== s) t.data = s;
        });
        el.appendChild(t);
      } else if (c instanceof Node) {
        el.appendChild(c);
      } else {
        el.appendChild(document.createTextNode(String(c)));
      }
    });
  }

  function h(tag, props, ...children) {
    const el = document.createElement(tag);
    Object.entries(props || {}).forEach(([key, value]) => {
      if (key.startsWith('on') && typeof value === 'function') {
        el.addEventListener(key.slice(2), value);
      } else if (typeof value === 'function') {
        applyProp(el, key, value());
        bindings.push(() => applyProp(el, key, value()));
      } else {
        applyProp(el, key, value);
      }
    });
    append(el, children);
    return el;
  }

  /** 把卡片滚进它所在的滚动区（页面本身不滚，各页在内嵌面板里滚动），再闪一下 */
  function scrollToCard(el, block = 'center') {
    el.scrollIntoView({ behavior: 'smooth', block });
    // 有的浏览器环境不执行平滑滚动，半秒后还不在视野里就直接跳过去
    setTimeout(() => {
      const r = el.getBoundingClientRect();
      if (r.top < 0 || r.top > window.innerHeight - 40) el.scrollIntoView({ block });
    }, 500);
    el.classList.remove('flash');
    void el.offsetWidth;
    el.classList.add('flash');
  }

  function bump(el) {
    el.classList.remove('bump');
    void el.offsetWidth;
    el.classList.add('bump');
  }

  // ---------- 状态 ----------
  let S = null;
  let D = {};
  const clone = (o) => JSON.parse(JSON.stringify(o));
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const fmt = (n) => Number(n).toLocaleString('en-US');
  const get = (g, k) => S.cfg[g][k];
  const has = (g) => !!(S && S.arg[g]);
  const isOn = (g) => !!(S.cfg[g] && S.cfg[g].Enable);

  function set(g, k, v) {
    S.cfg[g][k] = v;
    delete S.errors[g + '_' + k];
    S.justSaved = false;
    refresh();
  }

  function setError(key, msg) {
    if (msg) S.errors[key] = msg;
    else delete S.errors[key];
    refresh();
  }

  function parseItems(value) {
    const xs = String(value === undefined || value === null ? '' : value).split(/[,，\s]+/).filter(Boolean).map(Number)
      .filter((n) => Number.isInteger(n) && n > 0);
    return [...new Set(xs)].sort((a, b) => a - b);
  }

  // yaml 里的写法 ↔ 界面用的写法
  function toUi(data) {
    const cfg = clone(data);
    if (cfg.Vault) cfg.Vault.Items = parseItems(cfg.Vault.Items);
    if (cfg.MaterialRealm) {
      cfg.MaterialRealm.BuyCount = String(cfg.MaterialRealm.BuyCount).replace(/\D/g, '').padStart(4, '0').slice(0, 4).split('').map(Number);
    }
    return cfg;
  }

  function toData(cfg) {
    const data = clone(cfg);
    if (data.Vault) data.Vault.Items = data.Vault.Items.join(',');
    if (data.MaterialRealm) data.MaterialRealm.BuyCount = data.MaterialRealm.BuyCount.join('');
    return data;
  }

  function defaultsOf(argument) {
    const data = {};
    Object.entries(argument).forEach(([g, args]) => {
      data[g] = {};
      Object.entries(args).forEach(([k, def]) => {
        if (!k.startsWith('_')) data[g][k] = def.value;
      });
    });
    return toUi(data);
  }

  const OPEN_KEY = 'zjcs.gui.open';
  function loadOpen() {
    try {
      return new Set(JSON.parse(localStorage.getItem(OPEN_KEY) || '[]'));
    } catch (e) {
      return new Set();
    }
  }
  function saveOpen() {
    try {
      localStorage.setItem(OPEN_KEY, JSON.stringify([...S.open]));
    } catch (e) { /* 存不了就不记 */ }
  }
  function toggleOpen(id, force) {
    const open = force === undefined ? !S.open.has(id) : force;
    if (open) S.open.add(id);
    else S.open.delete(id);
    saveOpen();
    refresh();
  }

  const changed = (g) => !same(S.cfg[g], S.saved[g]);
  const errorOf = (key) => S.errors[key] || '';
  const groupHasError = (g) => Object.keys(S.errors).some((k) => k.startsWith(g + '_'));
  const detailKeys = (g) => Object.keys(S.cfg[g]).filter((k) => k !== 'Enable');
  const canReset = (g) => detailKeys(g).some((k) => !same(S.cfg[g][k], S.defaults[g][k]));

  function reset(g) {
    releaseFocus();
    detailKeys(g).forEach((k) => {
      S.cfg[g][k] = clone(S.defaults[g][k]);
      delete S.errors[g + '_' + k];
    });
    S.justSaved = false;
    refresh();
    toast('已恢复默认设置，记得保存');
  }

  // ---------- 规则、文案 ----------
  const DISCOUNTS = [3, 4, 5, 6, 7, 8, 9, '全部'];
  const DUNGEONS = [
    ['最新', '进去时默认显示的那个'],
    ['磐岩斗阵', '固定打这个副本'],
    ['曙光圣庭', '固定打这个副本'],
  ];
  const TOOLS = ['锤子', '镐子', '手套', '铲子'];
  const ARENA_PRICES = [10, 15, 20];
  const DONATE = [['第 1 次', '免费', 0], ['第 2 次', '20 晨星', 20], ['第 3 次', '50 晨星', 50]];
  const REWARD_EVENTS = [
    ['SignIn', '每日签到', '精彩活动里的每日签到', ''],
    ['Mibao', '秘宝大作战', '只领「获取能量」，不兑换封印宝藏', ''],
    ['Fate', '命运探索 1 次', '秘宝大作战的任务：去大地图探索一次', '用掉 1 枚命运果实'],
    ['Season', '赛季活动·晶芒淬炼', '三个页签里的「领取」', ''],
    ['Party', '惊魂派对', '惊奇日签、怪谈手册任务和基础奖励', ''],
  ];
  const REWARD_MENU = [
    ['Mall', '商城免费项', '每日赠礼和月卡每日奖励', ''],
    ['Pass', '巡礼之证', '目标经验和免费线等级奖励', ''],
    ['Friend', '好友友情币', '好友页底部的爱心按钮', ''],
    ['Gift', '馈赠总览', '战力、装备强化等里程碑奖励', ''],
    ['Task', '任务·日常', '日常任务的「领取」', ''],
    ['Commission', '任务·委托提交', '有「提交」的委托都提交', '会扣材料'],
  ];
  const SHORT = { SignIn: '签到', Mibao: '秘宝能量', Fate: '命运探索', Season: '晶芒淬炼', Party: '惊魂派对', Mall: '商城免费项', Pass: '巡礼之证', Friend: '友情币', Gift: '馈赠', Task: '日常任务', Commission: '委托提交' };
  const ROUTE = [
    ['公会', ['GuildIdleReward', 'GuildDonate', 'GuildWar', 'GuildRaid']],
    ['商店', ['GeneralShop', 'Vault']],
    ['日常领取', ['CandyTree', 'Cart', 'HomeHouse']],
    ['笔记', ['BondAdventure', 'FateFruit', 'Arena', 'MaterialRealm']],
    ['每日活动', ['HolyBeastTrial', 'TwinShadow']],
    ['限时活动', ['FenekPuzzle']],
    ['日常副本', ['DailyDungeon']],
    ['领取奖励', ['DailyReward']],
  ];
  const SETTINGS = ['Scheduler', 'Notify', 'Device'];
  // argument.yaml 里 _menu 是「设置」的分组放设置页，不算每天的任务（通知也有 Enable 开关，但不是任务）
  const isSetting = (g) => SETTINGS.includes(g) || (S.arg[g] && S.arg[g]._menu === '设置') || !('Enable' in S.cfg[g]);
  const LOCAL_TZ = -new Date().getTimezoneOffset() / 60;
  const tzLabel = (tz) => 'UTC' + (tz >= 0 ? '+' : '−') + Math.abs(tz);

  function ranges(list) {
    const out = [];
    let i = 0;
    while (i < list.length) {
      let j = i;
      while (j + 1 < list.length && list[j + 1] === list[j] + 1) j += 1;
      out.push(j - i >= 2 ? list[i] + '–' + list[j] : list.slice(i, j + 1).join('、'));
      i = j + 1;
    }
    return out.join('、');
  }

  function localTime(hhmm, tz) {
    const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm || '');
    if (!m) return '--:--';
    const total = Number(m[1]) * 60 + Number(m[2]) + Math.round((LOCAL_TZ - Number(tz)) * 60);
    const minutes = ((total % 1440) + 1440) % 1440;
    return String(Math.floor(minutes / 60)).padStart(2, '0') + ':' + String(minutes % 60).padStart(2, '0');
  }

  function arenaCost() {
    const tk = get('Arena', 'BuyTickets');
    const known = ARENA_PRICES.slice(0, Math.min(tk, 3));
    return { tk, known, sum: known.reduce((a, b) => a + b, 0), more: tk > 3 };
  }
  const donateCost = () => DONATE.slice(0, get('GuildDonate', 'Times')).reduce((a, s) => a + s[2], 0);

  const SPEC = {
    GeneralShop: {
      sentence() {
        const d = get('GeneralShop', 'Discount');
        const r = get('GeneralShop', 'RefreshTimes');
        const refresh = r < 0 ? '刷新到用光' : r === 0 ? '不刷新' : '刷新 ' + r + ' 次';
        return (String(d) === '全部' ? '一键买所有限购商品' : '一键买 ' + d + ' 折及以下的限购商品') + '，' + refresh;
      },
      panel: shopPanel,
    },
    Vault: {
      sentence() {
        const items = get('Vault', 'Items');
        return items.length ? '买第 ' + ranges(items) + ' 件，限购多次的买满' : '一件都不买';
      },
      cost: () => (get('Vault', 'Items').length ? '晨星按标价' : null),
      panel: vaultPanel,
    },
    CandyTree: {
      sentence: () => '有糖果就收；认不出就点树，进了卡池马上退出',
      panel: () => info(
        [h('ol', { class: 'plain', style: { 'padding-left': '20px', margin: '0' } },
          h('li', null, '在家园里找树上的糖果，认出来就点一下收获。'),
          h('li', null, '认不出时点一下树身；要是进了幻兽结缘卡池，说明树上没有糖果，马上返回。'))],
        '卡池里的「结缘」按钮绝不点。'),
    },
    Cart: {
      sentence: () => '点一下小推车，领挂机产出',
      panel: () => info([h('p', { class: 'plain' }, '在家园里找小推车头顶的奖杯气泡，点一下领挂机产出。没有气泡就跳过，不算失败。')]),
    },
    HomeHouse: {
      sentence: () => '床：领经验、用免费加速；信箱：有红点就全部领取',
      panel: () => [
        h('div', { class: 'minis' },
          h('div', { class: 'box' }, h('h3', null, '床'), h('ol', null, h('li', null, '领床上方的经验气泡'), h('li', null, '用「今日免费加速」（加速 2 小时）'), h('li', null, '加速产出的经验再领一次'))),
          h('div', { class: 'box' }, h('h3', null, '信箱'), h('ol', null, h('li', null, '信箱上有红点才打开'), h('li', null, '点「全部领取」')))),
        guard('「全局加速」要用道具，不点；信件的「删除已读」不点。'),
        h('p', { class: 'hint' }, '这一项没有要调的细节，用左边的开关决定做不做。'),
      ],
    },
    DailyDungeon: {
      sentence() {
        const dg = get('DailyDungeon', 'Dungeon');
        const buy = get('DailyDungeon', 'BuyExtra');
        return (dg === '最新' ? '打最新的副本' : '打「' + dg + '」') + '，选能打的最高难度；' + (buy ? '买满次数，每天 4 场' : '不买次数，每天 2 场') + '；S 评级才领奖';
      },
      cost: () => (get('DailyDungeon', 'BuyExtra') ? '250 晨星' : null),
      panel: dungeonPanel,
    },
    BondAdventure: {
      sentence() {
        const n = get('BondAdventure', 'RefreshLimit');
        return '领回完成的委派、派出新的；' + (n > 0 ? '品质不够时最多刷新 ' + n + ' 次' : '不刷新');
      },
      cost: () => (get('BondAdventure', 'RefreshLimit') > 0 ? '≤ ' + get('BondAdventure', 'RefreshLimit') * 100 + ' 晨星' : null),
      panel: bondPanel,
    },
    FateFruit: {
      sentence: () => '显示「可领取」就领免费的命运果实',
      panel: () => info([h('p', { class: 'plain' }, '笔记 → 地图探索：命运果实卡片的礼物下面写着「可领取」就点一下，领 1 个免费果实；显示倒计时就跳过。')]),
    },
    Arena: {
      sentence() {
        const tk = get('Arena', 'BuyTickets');
        return (tk > 0 ? '买 ' + tk + ' 张挑战券，' : '不买券，') + '扫荡最后一个对手 ' + get('Arena', 'Challenges') + ' 次';
      },
      cost() {
        const a = arenaCost();
        return a.tk > 0 ? a.sum + (a.more ? '+' : '') + ' 晨星' : null;
      },
      panel: arenaPanel,
    },
    MaterialRealm: {
      sentence() {
        const bc = get('MaterialRealm', 'BuyCount');
        return TOOLS.map((t, i) => t + ' ' + bc[i]).join(' · ') + ' 组，总价正好 ' + fmt(get('MaterialRealm', 'ExpectedCost')) + ' 才买；开采 ' + get('MaterialRealm', 'MineTimes') + ' 次';
      },
      cost: () => (get('MaterialRealm', 'ExpectedCost') > 0 ? fmt(get('MaterialRealm', 'ExpectedCost')) + ' 晨星' : null),
      panel: materialPanel,
    },
    HolyBeastTrial: {
      sentence: () => '匹配队友，等自动战斗打完，领进度奖励',
      panel: () => info([h('p', { class: 'plain' }, '匹配 → 接受 → 等全自动战斗打完 → 领进度奖励。一场大约 3 分钟。')]),
    },
    TwinShadow: {
      sentence: () => '和圣兽试炼一样自动打完，不开无尽模式',
      panel: () => info([h('p', { class: 'plain' }, '匹配 → 接受 → 等全自动战斗打完；不开无尽模式。一场大约 1 分半。')]),
    },
    GuildIdleReward: {
      sentence: () => '点远征之门下方的挂机卡片领取',
      panel: () => info([h('p', { class: 'plain' }, '公会 → 远征之门下方的挂机卡片，点一下直接领取；没有红点也能领。')]),
    },
    GuildDonate: {
      sentence: () => ['不捐', '捐 1 次（免费）', '捐 2 次（免费 + 20 晨星）', '捐 3 次（免费 + 20 + 50 晨星）'][get('GuildDonate', 'Times')],
      cost: () => (donateCost() > 0 ? donateCost() + ' 晨星' : null),
      panel: donatePanel,
    },
    GuildWar: {
      sentence() {
        const n = get('GuildWar', 'Challenges');
        return n > 0 ? '周一三五开放后打 ' + n + ' 场，只挑战力 ≤ 自己 ' + Math.round(get('GuildWar', 'PowerRatio') * 100) + '% 的对手' : '不打';
      },
      panel: warPanel,
    },
    GuildRaid: {
      sentence() {
        const n = get('GuildRaid', 'Challenges');
        return n > 0 ? '打 ' + n + ' 次，开战后马上返回，后台结算' : '不打';
      },
      panel: raidPanel,
    },
    FenekPuzzle: {
      sentence: () => '从当前关打到打不动为止，不用黄金甲虫',
      panel: () => info([h('p', { class: 'plain' }, '精彩活动 → 菲涅克的谜题：音符晶灯听旋律再按顺序敲晶石柱，元素链接自动连线铺满棋盘，石板谜题算出一笔点亮的路线再一格一格走，18 关都能解。只领每关的通关奖励，不点菲涅克的「帮我解谜」（要供奉黄金甲虫）。')]),
    },
    DailyReward: {
      sentence() {
        const keys = REWARD_EVENTS.concat(REWARD_MENU).map((r) => r[0]);
        const off = keys.filter((k) => !get('DailyReward', k));
        if (!off.length) return keys.length + ' 类奖励全部领取，付费和抽奖一律不点';
        if (off.length === keys.length) return '一类都不领';
        return '领 ' + (keys.length - off.length) + ' 类，跳过' + off.map((k) => SHORT[k]).join('、');
      },
      panel: rewardPanel,
    },
    Scheduler: {
      icon: 'clock',
      sentence: () => '你的电脑每天 ' + localTime(get('Scheduler', 'ServerUpdate'), get('Scheduler', 'ServerTimezone')) + ' 开始；同一项连续失败 ' + get('Scheduler', 'FailureLimit') + ' 次就停下',
      panel: schedulerPanel,
    },
    Notify: {
      sentence() {
        const on = [get('Notify', 'Human') && '需要你处理时', get('Notify', 'Finish') && '每天跑完时'].filter(Boolean);
        return on.length ? on.join('、') + '弹出' + (S.mac ? '系统' : ' Windows ') + '通知' : '开关开着，但两种情况都没选';
      },
      panel: notifyPanel,
    },
    Device: {
      icon: 'device',
      sentence: () => get('Device', 'Serial') + ' · 截图用 ' + get('Device', 'ScreenshotMethod') + ' · 间隔 ' + Number(get('Device', 'ScreenshotInterval')).toFixed(1) + ' 秒',
      panel: devicePanel,
    },
  };

  // ---------- 通用控件 ----------
  function guard(text) {
    return h('div', { class: 'guard' }, icon('shield', 18), h('span', null, text));
  }

  function info(body, guardText) {
    return [
      h('div', { class: 'field' }, h('h3', { class: 'q' }, '它会这样做'), ...body),
      guardText ? guard(guardText) : null,
      h('p', { class: 'hint' }, '这一项没有要调的细节，用左边的开关决定做不做。'),
    ];
  }

  function field(question, ...children) {
    return h('div', { class: 'field' }, typeof question === 'string' ? h('h3', { class: 'q' }, question) : question, ...children);
  }

  function errorLine(key) {
    return h('p', { class: 'field-error', show: () => !!errorOf(key) }, icon('alert', 15), h('span', null, () => errorOf(key)));
  }

  function rules(...items) {
    return h('div', { class: 'box' }, h('h4', null, '不用设置，它会自动'), h('ul', null, ...items.map((t) => h('li', null, t))));
  }

  /** 加减按钮。到头时用 aria-disabled 而不是 disabled，焦点不会丢 */
  function stepperOf(read, write, { min, max, step = 1, digits = 0, label }) {
    const fix = (x) => Number(x.toFixed(digits));
    const out = h('output', { 'aria-live': 'polite' }, () => (digits ? Number(read()).toFixed(digits) : String(read())));
    const change = (delta) => {
      const next = Math.min(max, Math.max(min, fix(Number(read()) + delta)));
      if (next === Number(read())) return;
      write(next);
      bump(out);
    };
    return h('div', { class: 'stepper', role: 'group', 'aria-label': label },
      h('button', { type: 'button', 'aria-label': '减少' + label, 'aria-disabled': () => String(Number(read()) <= min), onclick: () => change(-step) }, icon('minus', 18)),
      out,
      h('button', { type: 'button', 'aria-label': '增加' + label, 'aria-disabled': () => String(Number(read()) >= max), onclick: () => change(step) }, icon('plus', 18)));
  }
  const stepper = (g, k, opts) => stepperOf(() => get(g, k), (v) => set(g, k, v), opts);

  function choice(selected, pick, title, desc, extraClass = '') {
    return h('button', { type: 'button', class: 'choice ' + extraClass, 'aria-pressed': () => String(selected()), onclick: pick },
      h('span', { class: 'choice-title' }, title),
      desc ? h('span', { class: 'choice-desc' }, desc) : null,
      h('span', { class: 'tick' }, icon('check', 12)));
  }

  function switchRow(read, toggle, title, desc) {
    return h('button', { type: 'button', role: 'switch', class: 'toggle-card', 'aria-checked': () => String(!!read()), onclick: toggle },
      h('span', { class: 'tt' }, h('b', null, title), desc),
      h('span', { class: 'switch' }));
  }

  function textInput(g, k, { mono = false, check } = {}) {
    const key = g + '_' + k;
    return h('input', {
      class: () => 'input' + (mono ? ' mono' : '') + (errorOf(key) ? ' invalid' : ''),
      type: 'text',
      spellcheck: 'false',
      value: () => get(g, k),
      'aria-invalid': () => String(!!errorOf(key)),
      oninput: (e) => {
        const v = e.target.value.trim();
        S.cfg[g][k] = v;
        S.justSaved = false;
        setError(key, check ? check(v) : (v ? '' : '不能为空'));
      },
    });
  }

  // ---------- 各任务的面板 ----------
  function shopPanel() {
    const disc = () => DISCOUNTS.findIndex((d) => String(d) === String(get('GeneralShop', 'Discount')));
    const rt = () => get('GeneralShop', 'RefreshTimes');
    return [
      field('一键购买几折以内的限购商品？',
        h('div', { class: 'seg accent', role: 'group', 'aria-label': '一键购买折扣' }, DISCOUNTS.map((d, i) =>
          h('button', {
            type: 'button',
            class: () => (i < disc() ? 'covered' : ''),
            'aria-pressed': () => String(i === disc()),
            onclick: () => set('GeneralShop', 'Discount', d),
          }, d === '全部' ? '全部' : d + ' 折'))),
        h('p', { class: 'hint' }, '选中的折扣和更便宜的都会买（浅色的也包括在内），和游戏里「一键购买」的折扣滑块是同一个设置。')),
      field('买完要刷新商店再买吗？',
        h('div', { class: 'choices' },
          choice(() => rt() < 0, () => set('GeneralShop', 'RefreshTimes', -1), '刷新到用光', '刷一次买一轮，直到刷新次数用完'),
          choice(() => rt() === 0, () => set('GeneralShop', 'RefreshTimes', 0), '不刷新', '只买现在这一批'),
          choice(() => rt() > 0, () => { if (rt() <= 0) set('GeneralShop', 'RefreshTimes', 3); }, '指定次数', '刷几次由你定')),
        h('div', { class: 'inline', show: () => rt() > 0 },
          h('span', { class: 'unit' }, '每天刷新'),
          stepper('GeneralShop', 'RefreshTimes', { min: 1, max: 99, label: '刷新次数' }),
          h('span', { class: 'unit' }, '次')),
        h('p', { class: 'hint' }, '刷新价格是罗拉才刷；价格变成晨星或者弹出对话框就停，不会为刷新花晨星。')),
    ];
  }

  function vaultPanel() {
    const items = () => get('Vault', 'Items');
    const setItems = (xs) => set('Vault', 'Items', [...new Set(xs)].sort((a, b) => a - b));
    const extra = () => items().filter((n) => n > 9);
    return [
      field(h('div', { class: 'qrow', style: { 'max-width': '380px' } }, h('h3', { class: 'q' }, '买哪几件？'), h('span', { class: 'qmeta' }, () => (items().length ? '已选 ' + items().length + ' 件' : '一件都没选'))),
        h('p', { class: 'hint' }, '格子和游戏里宝库的排列一样：从左到右、从上到下数。'),
        h('div', { class: 'slots', role: 'group', 'aria-label': '要买的宝库商品' }, [1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => {
          const sel = () => items().includes(n);
          return h('button', {
            type: 'button',
            class: 'slot',
            'aria-label': '第 ' + n + ' 件',
            'aria-pressed': () => String(sel()),
            onclick: () => setItems(sel() ? items().filter((x) => x !== n) : items().concat([n])),
          }, h('span', { class: 'slot-n' }, String(n)), h('span', { class: 'slot-s' }, () => (sel() ? '要买' : '不买')), h('span', { class: 'tick' }, icon('check', 12)));
        })),
        h('div', { class: 'btn-row' },
          h('button', { type: 'button', class: 'btn', onclick: () => setItems([1, 2, 3, 4, 5].concat(extra())) }, '只买前 5 件'),
          h('button', { type: 'button', class: 'btn', onclick: () => setItems([1, 2, 3, 4, 5, 6, 7, 8, 9].concat(extra())) }, '全选'),
          h('button', { type: 'button', class: 'btn', onclick: () => setItems(extra()) }, '全不选')),
        h('p', { class: 'hint', show: () => extra().length > 0 }, () => '配置里还有第 ' + extra().join('、') + ' 件：要滑动才看得到，脚本暂时会跳过。'),
        h('p', { class: 'hint' }, '已售罄的自动跳过；「限购 2 次」这类会买满。点价格就直接买，游戏不会再确认。第 10 件以后要滑动，暂时不支持。')),
    ];
  }

  function dungeonPanel() {
    return [
      field('打哪个副本？',
        h('div', { class: 'choices' }, DUNGEONS.map(([name, desc]) =>
          choice(() => get('DailyDungeon', 'Dungeon') === name, () => set('DailyDungeon', 'Dungeon', name), name, desc)))),
      field('每天买额外的领奖次数吗？',
        switchRow(() => get('DailyDungeon', 'BuyExtra'), () => set('DailyDungeon', 'BuyExtra', !get('DailyDungeon', 'BuyExtra')),
          () => (get('DailyDungeon', 'BuyExtra') ? '买满 2 次，每天打 4 场' : '不买，每天打 2 场'),
          h('span', { class: 'cost-note' }, icon('diamond', 11), '买 2 次共 250 晨星（第 1 次 100，第 2 次 150）')),
        h('p', { class: 'hint' }, '今天已经买过就不会重复买：价格对不上会取消。')),
      rules('选能打的最高难度。', 'S 评级才领奖；不是 S 就不领、重新匹配，一直打到领奖次数用完。'),
    ];
  }

  function bondPanel() {
    const n = () => get('BondAdventure', 'RefreshLimit');
    return [
      field('委派品质不够时，每天最多刷新几次？',
        h('div', { class: 'inline' },
          stepper('BondAdventure', 'RefreshLimit', { min: 0, max: 3, label: '刷新次数' }),
          h('span', { class: 'cost-note' }, icon('diamond', 11), () => (n() > 0 ? '最多 ' + n() * 100 + ' 晨星' : '不花晨星'))),
        h('p', { class: 'hint' }, '每次 100 晨星。只在 4 个委派里紫色及以上不到 2 个时才刷；价格不是 100 就不刷。')),
      rules('先领回已完成的委派，再派新的。', '有橙色委派，先把橙色派出去。', '只做奇景委派，不点「挑战」。'),
    ];
  }

  function arenaPanel() {
    return [
      h('div', { class: 'cols' },
        field('每天买几张挑战券？',
          h('div', { class: 'inline' }, stepper('Arena', 'BuyTickets', { min: 0, max: 8, label: '挑战券' }), h('span', { class: 'unit' }, '张')),
          h('span', { class: 'cost-note' }, icon('diamond', 11), () => {
            const a = arenaCost();
            if (a.tk === 0) return '不买，不花晨星';
            if (a.tk === 1) return '1 张 10 晨星';
            if (a.more) return a.tk + ' 张，至少 ' + a.sum + ' 晨星（第 4 张起的价格还没实测）';
            return a.tk + ' 张共 ' + a.sum + ' 晨星（' + a.known.join(' + ') + '）';
          })),
        field('挑战几次？',
          h('div', { class: 'inline' }, stepper('Arena', 'Challenges', { min: 0, max: 10, label: '挑战次数' }), h('span', { class: 'unit' }, '次')),
          h('p', { class: 'hint' }, '每次挑战列表里最后一个对手，扫荡直接出结果。'))),
      h('p', { class: 'hint' }, '挑战券每天限购 8 张，一张比一张贵。'),
    ];
  }

  function materialPanel() {
    const bc = () => get('MaterialRealm', 'BuyCount');
    const key = 'MaterialRealm_ExpectedCost';
    return [
      field('一键购买：每种工具买几组？',
        h('div', { class: 'choices four' }, TOOLS.map((name, i) =>
          h('div', { class: 'box', style: { gap: '8px', 'align-items': 'flex-start' } },
            h('b', null, name),
            stepperOf(() => bc()[i], (v) => {
              const next = bc().slice();
              next[i] = v;
              set('MaterialRealm', 'BuyCount', next);
            }, { min: 0, max: 9, label: name + '组数' }),
            h('span', { class: 'hint' }, '组'))))),
      field(h('label', { class: 'q', for: 'mat-expected' }, '游戏显示的总价正好是多少，才买？'),
        h('div', { class: () => 'money' + (errorOf(key) ? ' invalid' : '') },
          icon('diamond', 14),
          h('input', {
            id: 'mat-expected',
            inputmode: 'numeric',
            value: () => get('MaterialRealm', 'ExpectedCost'),
            'aria-invalid': () => String(!!errorOf(key)),
            oninput: (e) => {
              const v = e.target.value.replace(/[,\s]/g, '');
              if (/^\d{1,6}$/.test(v)) set('MaterialRealm', 'ExpectedCost', Number(v));
              else setError(key, '要填 0 或正整数');
            },
          }),
          h('span', null, '晨星')),
        errorLine(key),
        h('p', { class: 'hint' }, '调好组数后，游戏里的总价必须正好等于这个数才会点购买；价格变了就跳过这一步，防止多花。')),
      field('买完去黄金矿洞开采几次？',
        h('div', { class: 'inline' }, stepper('MaterialRealm', 'MineTimes', { min: 0, max: 30, label: '开采次数' }), h('span', { class: 'unit' }, '次')),
        h('p', { class: 'hint' }, '每次用 1 把镐子；不开快捷开采。')),
    ];
  }

  function donatePanel() {
    const n = () => get('GuildDonate', 'Times');
    return [
      field(h('div', { class: 'qrow' }, h('h3', { class: 'q' }, '每天捐几次？'),
        h('span', { class: 'cost-note', style: { 'font-size': '14px' } }, icon('diamond', 11), () => (donateCost() > 0 ? '每天 ' + donateCost() + ' 晨星' : n() > 0 ? '不花晨星' : '不捐'))),
        h('div', { class: 'choices four' },
          DONATE.map(([label, price], i) => h('button', {
            type: 'button',
            class: 'choice',
            'aria-pressed': () => String(i < n()),
            'aria-label': label + '，' + price,
            onclick: () => set('GuildDonate', 'Times', i + 1),
          }, h('span', { class: 'choice-sub' }, label), h('span', { class: 'choice-big' }, price), h('span', { class: 'tick' }, icon('check', 12)))),
          h('div', { class: 'choice static' }, h('span', { class: 'choice-sub' }, '第 4 次'), h('span', { class: 'choice-big' }, '100 晨星 · 不做'))),
        h('div', { class: 'btn-row' }, h('button', { type: 'button', class: 'btn', onclick: () => set('GuildDonate', 'Times', 0) }, '一次都不捐')),
        h('p', { class: 'hint' }, '点第几张就捐到第几次。游戏按钮上的价格要和这里一样才会点，对不上就停。')),
    ];
  }

  function warPanel() {
    const pct = () => Math.round(get('GuildWar', 'PowerRatio') * 100);
    return [
      field('什么时候打',
        h('div', { class: 'days', 'aria-hidden': 'true' }, ['一', '二', '三', '四', '五', '六', '日'].map((d, i) => h('span', { class: 'day' + (i % 2 === 0 && i < 6 ? ' on' : '') }, d))),
        h('p', { class: 'plain' }, '周一、三、五 11:00–23:00 开放（你电脑上的时间）。早上跑到这里还没开放，会在 11:01 自动再跑一次。')),
      field('每天打几场？',
        h('div', { class: 'inline' }, stepper('GuildWar', 'Challenges', { min: 0, max: 3, label: '场数' }), h('span', { class: 'unit' }, '场（最多 3 场）'))),
      h('div', { class: 'slider' },
        h('div', { class: 'qrow' }, h('label', { class: 'q', for: 'war-ratio' }, '只挑多弱的对手？'), h('span', { class: 'big-pct', 'aria-hidden': 'true' }, () => pct() + '%')),
        h('input', {
          id: 'war-ratio',
          class: 'range',
          type: 'range',
          min: '50',
          max: '100',
          step: '5',
          value: () => pct(),
          'aria-valuetext': () => '自己战力的 ' + pct() + '%',
          style: () => ({ '--p': ((pct() - 50) * 2) + '%' }),
          oninput: (e) => set('GuildWar', 'PowerRatio', Number(e.target.value) / 100),
        }),
        h('div', { class: 'range-ends' }, h('span', null, '50% 更稳'), h('span', null, '100% 和自己一样强')),
        h('div', { class: 'example' }, '比如你的战力是 20 亿 → 只打 ', h('strong', null, () => (20 * pct()) / 100 + ' 亿'), ' 及以下的对手')),
      rules('进地图后从最上面往下找，第一个符合的就打。', '盖了「击破」「已挑战」章的打不了，直接跳过；打过的不再打。', '弹窗里剩余挑战次数为 0 就结束。'),
    ];
  }

  function raidPanel() {
    return [
      field('每天打几次？',
        h('div', { class: 'inline' }, stepper('GuildRaid', 'Challenges', { min: 0, max: 2, label: '讨伐次数' }), h('span', { class: 'unit' }, '次（每天最多 2 次）')),
        h('p', { class: 'hint' }, '开始战斗后马上最小化返回，战斗在后台结算；左上角剩余次数变成 0 就算完成。')),
    ];
  }

  function rewardPanel() {
    const list = (rows) => h('div', { class: 'tlist' }, rows.map(([key, name, desc, note]) =>
      h('button', {
        type: 'button',
        role: 'switch',
        class: 'titem',
        'aria-checked': () => String(!!get('DailyReward', key)),
        onclick: () => set('DailyReward', key, !get('DailyReward', key)),
      },
      h('span', { class: 'tt' }, h('span', { class: 'titem-name' }, name), h('span', { class: 'titem-desc' }, desc)),
      note ? h('span', { class: 'note' }, note) : null,
      h('span', { class: 'switch' }))));
    const count = () => REWARD_EVENTS.concat(REWARD_MENU).filter((r) => get('DailyReward', r[0])).length;
    return [
      h('div', { class: 'qrow' }, h('h3', { class: 'q' }, '领哪些奖励？'), h('span', { class: 'qmeta' }, () => '开了 ' + count() + ' / ' + (REWARD_EVENTS.length + REWARD_MENU.length) + ' 类')),
      h('div', { class: 'cols' },
        h('div', { class: 'tgroup' }, h('h4', null, '精彩活动'), list(REWARD_EVENTS)),
        h('div', { class: 'tgroup' }, h('h4', null, '主菜单'), list(REWARD_MENU))),
      guard('刮刮乐、卡池和付费按钮在任何页面都不点；入口没有红点就跳过。'),
    ];
  }

  function schedulerPanel() {
    const key = 'Scheduler_ServerUpdate';
    const tzOptions = () => {
      const base = [7, 8, 9];
      const cur = Number(get('Scheduler', 'ServerTimezone'));
      return base.includes(cur) ? base : base.concat([cur]).sort((a, b) => a - b);
    };
    const select = h('select', {
      class: 'input narrow',
      onchange: (e) => set('Scheduler', 'ServerTimezone', Number(e.target.value)),
    }, tzOptions().map((tz) => h('option', { value: String(tz) }, tzLabel(tz) + (tz === 8 ? '（北京时间）' : ''))));
    select.value = String(get('Scheduler', 'ServerTimezone'));
    bindings.push(() => { if (document.activeElement !== select) select.value = String(get('Scheduler', 'ServerTimezone')); });
    return [
      field('游戏每天几点刷新？',
        h('div', { class: 'inline', style: { 'align-items': 'flex-end', gap: '12px' } },
          h('label', { class: 'lf' }, '服务器时间', h('input', {
            class: () => 'input narrow' + (errorOf(key) ? ' invalid' : ''),
            type: 'time',
            value: () => get('Scheduler', 'ServerUpdate'),
            oninput: (e) => {
              const v = e.target.value;
              if (/^\d{2}:\d{2}$/.test(v)) set('Scheduler', 'ServerUpdate', v);
              else setError(key, '要写成 08:00 这样的时间');
            },
          })),
          h('label', { class: 'lf' }, '服务器时区', select)),
        errorLine(key),
        h('div', { class: 'callout' }, icon('clock', 18),
          h('span', null, '换算成你电脑上的时间（' + tzLabel(LOCAL_TZ) + '）：每天 ', h('strong', null, () => localTime(get('Scheduler', 'ServerUpdate'), get('Scheduler', 'ServerTimezone'))), ' 开始跑'))),
      field('同一项连续失败几次，就停下来等你？',
        h('div', { class: 'inline' }, stepper('Scheduler', 'FailureLimit', { min: 1, max: 10, label: '失败次数上限' }), h('span', { class: 'unit' }, '次')),
        h('p', { class: 'hint' }, '每次失败都会保存最近的截图并马上重试；连续失败到这个次数就停下，等你来看。')),
    ];
  }

  function devicePanel() {
    return [
      h('p', { class: 'plain' }, '换模拟器或者换电脑时才需要改这里。'),
      h('div', { class: 'cols' },
        h('label', { class: 'lf' }, '设备序列号', textInput('Device', 'Serial'), errorLine('Device_Serial'), h('span', { class: 'hint' }, S.arg.Device.Serial.help)),
        h('label', { class: 'lf' }, '游戏包名', textInput('Device', 'PackageName'), errorLine('Device_PackageName'))),
      h('label', { class: 'lf' }, 'adb 路径', textInput('Device', 'AdbExecutable', { mono: true }), errorLine('Device_AdbExecutable'), h('span', { class: 'hint' }, S.mac ? S.arg.Device.AdbExecutable.help : '默认是脚本自带的 bin\\adb\\adb.exe，一般不用改')),
      S.mac ? null : switchRow(() => get('Device', 'ReplaceAdb'), () => set('Device', 'ReplaceAdb', !get('Device', 'ReplaceAdb')), '替换雷电的 adb',
        '打开时把雷电目录里的 adb.exe 换成自带的那份（原文件改名 adb.exe.bak），会先结束所有 adb 进程。版本一致，雷电、别的脚本和这里就不会互相断线。'),
      h('div', { class: 'cols' },
        h('div', { class: 'field' }, h('h3', { class: 'lf' }, '截图方式'),
          h('div', { class: 'seg', role: 'group', 'aria-label': '截图方式' }, ['adb_raw', 'adb_png'].map((m) =>
            h('button', { type: 'button', 'aria-pressed': () => String(get('Device', 'ScreenshotMethod') === m), onclick: () => set('Device', 'ScreenshotMethod', m), style: { padding: '0 16px' } }, m === 'adb_raw' ? 'adb_raw（推荐）' : m)))),
        h('div', { class: 'field' }, h('h3', { class: 'lf' }, '两次截图最少隔多久'),
          h('div', { class: 'inline' }, stepper('Device', 'ScreenshotInterval', { min: 0.1, max: 2, step: 0.1, digits: 1, label: '截图间隔' }), h('span', { class: 'unit' }, '秒')))),
      deviceCheck(),
    ];
  }

  // 设备检测：按已保存的设置跑一遍 adb，只截图、不点任何东西
  const DC = { busy: false, result: null };
  function deviceCheck() {
    const steps = h('div', { class: 'check-steps' });
    const shot = h('img', { class: 'check-shot', alt: '模拟器当前画面' });
    bindings.push(() => {
      const r = DC.result;
      if (steps.dataset.sig === JSON.stringify(r && r.steps)) return;
      steps.dataset.sig = JSON.stringify(r && r.steps);
      steps.replaceChildren(...(r ? r.steps.map((s) => h('div', { class: 'check-step ' + (s.ok ? 'ok' : 'bad') },
        icon(s.ok ? 'check' : 'x', 14), h('b', null, s.name), h('span', null, s.detail))) : []));
      shot.hidden = !(r && r.image);
      if (r && r.image) shot.src = 'data:image/png;base64,' + r.image;
    });
    const deviceDirty = () => changed('Device');
    return h('div', { class: 'field check' },
      h('div', { class: 'qrow' }, h('h3', { class: 'q' }, '连得上吗？'),
        h('button', { type: 'button', class: 'btn', 'aria-busy': () => String(DC.busy), onclick: checkDevice },
          h('span', { class: 'spinner', 'aria-hidden': 'true', show: () => DC.busy }), () => (DC.busy ? '正在检查…' : DC.result ? '再检查一次' : '检查连接'))),
      h('p', { class: 'hint', show: () => deviceDirty() }, '检查用的是已保存的设置，上面改过的先保存再检查。'),
      h('p', { class: 'hint', show: () => !DC.result && !deviceDirty() }, '依次看 adb 能不能用、模拟器在不在线、能不能截图、游戏在不在前台。只截一张图，不会点游戏。'),
      h('div', { class: 'check-body', show: () => !!DC.result }, steps, shot));
  }

  async function checkDevice() {
    if (DC.busy) return;
    DC.busy = true;
    refresh();
    const r = await post('/api/device/check');
    DC.busy = false;
    if (r.ok) {
      DC.result = r.data;
      toast(r.data.ok ? '设备连接正常' : '有一项没通过，看看下面的说明', r.data.ok ? 'ok' : 'error');
    }
    refresh();
  }

  function notifyPanel() {
    return [
      h('div', { class: 'tlist', style: { 'max-width': '600px' } },
        [['Human', '需要你处理时', '连续失败到上限、模拟器不在线、脚本出错停下时'], ['Finish', '每天跑完时', '常驻运行时，到期的任务都做完了，发一条完成几项、失败几项的汇总']].map(([key, name, desc]) =>
          h('button', { type: 'button', role: 'switch', class: 'titem', 'aria-checked': () => String(!!get('Notify', key)), onclick: () => set('Notify', key, !get('Notify', key)) },
            h('span', { class: 'tt' }, h('span', { class: 'titem-name' }, name), h('span', { class: 'titem-desc' }, desc)),
            h('span', { class: 'switch' })))),
      h('div', { class: 'inline' },
        h('button', { type: 'button', class: 'btn', 'aria-busy': () => String(NT.busy), onclick: testNotify }, icon('bell', 16), () => (NT.busy ? '正在发送…' : '发一条测试通知')),
        h('span', { class: 'hint' }, S.mac ? '通知从屏幕右上角弹出，也会留在通知中心。第一次发时如果没弹出，到「系统设置 → 通知」里允许「脚本编辑器」发通知。' : '通知从屏幕右下角弹出，也会留在 Windows 通知中心。')),
    ];
  }

  const NT = { busy: false };
  async function testNotify() {
    if (NT.busy) return;
    NT.busy = true;
    refresh();
    const r = await post('/api/notify/test');
    NT.busy = false;
    refresh();
    if (r.ok) toast(r.data.ok ? '已发送，看看屏幕右下角' : '没发出去：' + (r.data.error || '未知原因'), r.data.ok ? 'ok' : 'error');
  }

  /** argument.yaml 里新增、界面还没专门设计的分组，按参数类型自动生成 */
  function genericPanel(g) {
    const args = Object.entries(S.arg[g]).filter(([k]) => !k.startsWith('_') && k !== 'Enable');
    if (!args.length) return info([h('p', { class: 'plain' }, S.arg[g].Enable && S.arg[g].Enable.help ? S.arg[g].Enable.help : '用左边的开关决定做不做。')]);
    return args.map(([k, def]) => {
      const help = def.help ? h('p', { class: 'hint' }, def.help) : null;
      if (def.type === 'checkbox') return switchRow(() => get(g, k), () => set(g, k, !get(g, k)), def.name, help);
      if (def.type === 'select') {
        return field(def.name, h('div', { class: 'seg' }, def.option.map((o) =>
          h('button', { type: 'button', 'aria-pressed': () => String(String(get(g, k)) === String(o)), onclick: () => set(g, k, o) }, String(o)))), help);
      }
      if (def.type === 'number' || def.type === 'float') {
        const float = def.type === 'float';
        return field(def.name, stepper(g, k, { min: float ? 0 : -1, max: 9999, step: float ? 0.1 : 1, digits: float ? 1 : 0, label: def.name }), help);
      }
      return field(def.name, textInput(g, k, { check: () => '' }), help);
    });
  }

  // ---------- 任务卡片和分组（每天的路线） ----------
  const specOf = (g) => SPEC[g] || { sentence: () => (S.arg[g].Enable && S.arg[g].Enable.help) || '', panel: () => genericPanel(g) };

  function taskCard(g) {
    const spec = specOf(g);
    const name = S.arg[g]._name || g;
    const noSwitch = !('Enable' in S.cfg[g]);
    const on = () => noSwitch || isOn(g);
    const open = () => S.open.has(g);
    const panelId = 'panel-' + g;
    const head = h('div', { class: 'card-head' },
      noSwitch
        ? h('span', { class: 'switch-slot', 'aria-hidden': 'true' }, icon(spec.icon || 'sliders', 18))
        : h('button', { type: 'button', class: 'switch-slot', role: 'switch', 'aria-label': name, 'aria-checked': () => String(on()), onclick: () => set(g, 'Enable', !on()) }, h('span', { class: 'switch' })),
      h('button', { type: 'button', class: 'row-btn', 'aria-expanded': () => String(open()), 'aria-controls': panelId, onclick: () => toggleOpen(g) },
        h('span', { class: 'row-text' },
          h('span', { class: 'row-title' },
            h('span', { class: 'row-name' }, name),
            h('span', { class: 'badge', show: () => changed(g) && !groupHasError(g) }, '已修改'),
            h('span', { class: 'badge error', show: () => groupHasError(g) }, '需要改一下')),
          h('span', { class: 'row-sentence' }, () => (on() ? spec.sentence() : '今天跳过这一项'))),
        spec.cost ? h('span', { class: 'chip-cost', show: () => on() && !!spec.cost() }, icon('diamond', 10), h('span', null, () => spec.cost() || '')) : null,
        icon('chev', 18, 'chev')));
    const inner = h('div', { class: 'card-inner' },
      spec.panel(),
      h('div', { class: 'reset-row', show: () => canReset(g) }, h('button', { type: 'button', class: 'btn btn-sm', onclick: () => reset(g) }, '恢复这一项的默认设置')));
    return h('div', {
      class: () => 'card' + (open() ? ' open' : '') + (on() ? '' : ' off') + (groupHasError(g) ? ' has-error' : ''),
      id: 'task-' + g,
    }, head, h('div', { class: 'card-panel', id: panelId, role: 'region', 'aria-label': name + '的细节', inert: () => !open() }, h('div', { class: 'card-clip' }, inner)));
  }

  function routeGroup(index, title, tasks, last) {
    const ids = tasks.filter(has);
    if (!ids.length) return null;
    const count = () => ids.filter(isOn).length;
    return h('section', { class: 'group', 'aria-label': title },
      h('div', { class: 'rail', 'aria-hidden': 'true' },
        h('span', { class: () => 'node' + (count() > 0 ? ' on' : '') }, String(index)),
        last ? null : h('span', { class: 'rail-line' })),
      h('div', { class: 'group-body' },
        h('div', { class: 'group-head' }, h('h2', null, title), h('span', { class: 'group-count' }, () => count() + ' / ' + ids.length + ' 项开启')),
        ids.map(taskCard)));
  }

  // ---------- 改动统计、晨星花费 ----------
  function derive() {
    let changes = 0;
    Object.keys(S.cfg).forEach((g) => Object.keys(S.cfg[g]).forEach((k) => {
      if (!same(S.cfg[g][k], (S.saved[g] || {})[k])) changes += 1;
    }));
    const costs = [];
    const add = (g, label, amount, n) => { if (has(g) && isOn(g) && n > 0) costs.push({ label, amount, n }); };
    if (has('MaterialRealm')) add('MaterialRealm', '素材秘境', fmt(get('MaterialRealm', 'ExpectedCost')), get('MaterialRealm', 'ExpectedCost'));
    if (has('BondAdventure')) add('BondAdventure', '羁绊冒险刷新', '最多 ' + get('BondAdventure', 'RefreshLimit') * 100, get('BondAdventure', 'RefreshLimit') * 100);
    if (has('DailyDungeon')) add('DailyDungeon', '日常副本次数', '250', get('DailyDungeon', 'BuyExtra') ? 250 : 0);
    if (has('GuildDonate')) add('GuildDonate', '公会捐赠', String(donateCost()), donateCost());
    let more = false;
    if (has('Arena')) {
      const a = arenaCost();
      add('Arena', '竞技场挑战券', a.sum + (a.more ? '+' : ''), a.sum);
      more = isOn('Arena') && a.more;
    }
    const total = costs.reduce((s, x) => s + x.n, 0);
    const tasks = Object.keys(S.arg).filter((g) => !isSetting(g));
    const pageChanges = { route: 0, settings: 0 };
    Object.keys(S.cfg).forEach((g) => { if (changed(g) || groupHasError(g)) pageChanges[isSetting(g) ? 'settings' : 'route'] += 1; });
    D = { changes, costs, total, more, enabled: tasks.filter(isOn).length, tasks: tasks.length, pageChanges };
  }

  /** 跳到某一项：路线上的展开卡片，设置里的直接滚过去，再闪一下 */
  function jumpTo(g) {
    const toSettings = isSetting(g);
    if (!toSettings) toggleOpen(g, true);
    go(toSettings ? 'settings' : 'route');
    setTimeout(() => {
      const el = document.getElementById('task-' + g);
      if (el) scrollToCard(el, toSettings ? 'start' : 'center');
    }, 80);
  }

  // ---------- 路线页右栏：概览 ----------
  function overview() {
    const totalEl = h('span', { class: 'big gold' }, '0');
    let shown = null;
    let raf = 0;
    let finish = 0;
    bindings.push(() => {
      const target = D.total;
      const suffix = D.more ? '+' : '';
      if (shown === null || shown === target) {
        shown = target;
        totalEl.textContent = fmt(target) + suffix;
        return;
      }
      cancelAnimationFrame(raf);
      const from = shown;
      const start = performance.now();
      const step = (now) => {
        const p = Math.min(1, (now - start) / 420);
        shown = Math.round(from + (target - from) * (1 - Math.pow(1 - p, 3)));
        totalEl.textContent = fmt(shown) + (p === 1 ? suffix : '');
        if (p < 1) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
      // 后台标签页里动画帧会被限速，到点直接显示准确的数
      clearTimeout(finish);
      finish = setTimeout(() => {
        cancelAnimationFrame(raf);
        shown = target;
        totalEl.textContent = fmt(target) + suffix;
      }, 480);
    });

    const costList = h('div', { class: 'cost-list' });
    let costSig = '';
    bindings.push(() => {
      const sig = JSON.stringify(D.costs);
      if (sig === costSig) return;
      const fresh = costSig === '';
      costSig = sig;
      const old = new Map([...costList.children].map((el) => [el.dataset.label, el]));
      costList.replaceChildren();
      if (!D.costs.length) {
        costList.append(h('div', { class: 'empty-cost' }, '今天不会花晨星'));
        return;
      }
      D.costs.forEach((x) => {
        const width = Math.max(4, Math.round((x.n / D.total) * 100)) + '%';
        let row = old.get(x.label);
        if (row) {
          row.querySelector('b').textContent = x.amount;
          requestAnimationFrame(() => { row.querySelector('i').style.width = width; });
          row.style.animation = 'none';
        } else {
          const bar = h('i', { style: { width: fresh ? width : '0%' } });
          row = h('div', { class: 'cost-row', 'data-label': x.label },
            h('div', { class: 'cost-line' }, h('span', null, x.label), h('b', null, x.amount)),
            h('div', { class: 'bar' }, bar));
          if (!fresh) requestAnimationFrame(() => requestAnimationFrame(() => { bar.style.width = width; }));
        }
        costList.append(row);
      });
    });

    const never = ['抽卡、扭蛋和结缘卡池', '幸运刮刮乐、惊吓南瓜', '任何付费按钮和礼包', '删除信件、用加速道具', '羁绊冒险的「挑战」'];
    return h('aside', { class: 'overview', 'aria-label': '概览' },
      has('Scheduler') ? h('div', { class: 'block' },
        h('h2', null, icon('clock', 16), '什么时候跑'),
        h('div', { class: 'big-row' }, h('span', null, '每天'), h('span', { class: 'big' }, () => localTime(get('Scheduler', 'ServerUpdate'), get('Scheduler', 'ServerTimezone')))),
        h('p', null, () => '游戏在服务器时间 ' + get('Scheduler', 'ServerUpdate') + ' 刷新，刷新后自动开始。公会战没开放时，等到 11:01 再跑。'),
        h('button', { type: 'button', class: 'btn btn-sm', onclick: () => jumpTo('Scheduler') }, '改时间')) : null,
      h('div', { class: 'block' },
        h('h2', null, icon('diamond', 12, 'gem'), '每天最多花多少晨星'),
        h('div', { class: 'big-row' }, totalEl, h('span', null, '晨星')),
        costList,
        h('p', { class: 'hint' }, '宝库按商品标价另算；羁绊刷新只在委派品质不够时才花。改了设置，这里马上跟着变。')),
      h('div', { class: 'block' },
        h('h2', null, icon('shield', 16, 'safe'), '不管怎么设置，都不会做'),
        h('ul', { class: 'never' }, never.map((t) => h('li', null, icon('ban', 14), h('span', null, t))))));
  }

  // ---------- 深浅色：跟随系统 / 浅色 / 深色，选择记在 localStorage ----------
  const THEME_KEY = 'zjcs.gui.theme';
  const THEMES = [['auto', 'monitor', '跟随系统'], ['light', 'sun', '浅色'], ['dark', 'moon', '深色']];
  const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');
  let themeMode = 'auto';
  let themeTimer = 0;
  try {
    themeMode = localStorage.getItem(THEME_KEY) || 'auto';
  } catch (e) { /* 读不到就跟随系统 */ }

  function applyTheme(animate) {
    const root = document.documentElement;
    const dark = themeMode === 'dark' || (themeMode === 'auto' && darkQuery.matches);
    if (animate) {
      root.classList.add('theme-switching');
      clearTimeout(themeTimer);
      themeTimer = setTimeout(() => root.classList.remove('theme-switching'), 400);
    }
    root.setAttribute('data-theme', dark ? 'dark' : 'light');
  }

  function setTheme(mode) {
    themeMode = mode;
    try {
      localStorage.setItem(THEME_KEY, mode);
    } catch (e) { /* 存不了就只管这一次 */ }
    applyTheme(true);
    refresh();
    toast(mode === 'auto' ? '外观跟随系统' + (darkQuery.matches ? '（现在是深色）' : '（现在是浅色）') : '已切到' + (mode === 'dark' ? '深色' : '浅色'));
  }

  darkQuery.addEventListener('change', () => { if (themeMode === 'auto') { applyTheme(true); refresh(); } });
  applyTheme(false);
  const isDark = () => document.documentElement.getAttribute('data-theme') === 'dark';

  function themeSeg() {
    return h('div', { class: 'seg', role: 'group', 'aria-label': '外观' }, THEMES.map(([mode, ic, label]) =>
      h('button', { type: 'button', 'aria-pressed': () => String(themeMode === mode), onclick: () => setTheme(mode), style: { display: 'inline-flex', 'align-items': 'center', gap: '6px' } }, icon(ic, 14), label)));
  }

  // ---------- 桌面壳：窗口按钮、拖动、迷你模式 ----------
  // 新版桌面壳（main.rs）提供 desktop_info / window_action 两个命令；浏览器和旧版桌面壳没有，页面照常用，只是缩不了窗口
  const DESK = { ok: false, platform: '', frameless: false };
  const tauri = () => window.__TAURI_INTERNALS__;

  async function initDesktop() {
    const T = tauri();
    if (!T || typeof T.invoke !== 'function') return null;
    try {
      // 旧版桌面壳没有这个命令，会直接拒绝；万一一直不回，1.5 秒后当作没有，免得页面卡在「正在读取配置」
      const info = await Promise.race([T.invoke('desktop_info'), new Promise((_, no) => setTimeout(() => no(new Error('timeout')), 1500))]);
      DESK.ok = true;
      DESK.platform = info.platform;
      DESK.frameless = !!info.frameless;
      const root = document.documentElement;
      root.classList.add('desk');
      root.classList.toggle('desk-mac', info.platform === 'macos');
      root.classList.toggle('desk-frameless', DESK.frameless);
      return info;
    } catch (e) {
      return null;
    }
  }

  function winAction(action) {
    if (!DESK.ok) return Promise.resolve(false);
    return tauri().invoke('window_action', { action }).then(() => true, () => false);
  }

  // 顶栏、侧栏标题、迷你模式顶条可以拖动窗口。照 Tauri 自带的拖动区（drag.js）：按下时 preventDefault，
  // 不然 WebKit 自己开始选字，窗口拖不动；双击最大化/还原，Mac 上在第二次松开、且鼠标没动时才做（和系统一致）
  const inDrag = (e) => !!e.target.closest('.drag') && !e.target.closest('button, a, input, select, textarea, label, summary, [role="switch"], .nodrag');
  let dblAt = null;
  document.addEventListener('mousedown', (e) => {
    if (!DESK.ok || e.button !== 0 || (e.detail !== 1 && e.detail !== 2) || !inDrag(e)) return;
    if (DESK.platform === 'macos' && e.detail === 2) {
      dblAt = [e.clientX, e.clientY];
      return;
    }
    e.preventDefault();
    winAction(e.detail === 2 ? 'max' : 'drag');
  });
  document.addEventListener('mouseup', (e) => {
    if (!dblAt || e.button !== 0) return;
    const [x, y] = dblAt;
    dblAt = null;
    if (e.detail === 2 && e.clientX === x && e.clientY === y && inDrag(e)) winAction('max');
  });

  function winctl() {
    const b = (action, title, ic, cls) => h('button', { type: 'button', class: cls || null, title, 'aria-label': title, onclick: () => winAction(action) }, icon(ic, 15));
    return h('div', { class: 'winctl' }, b('min', '最小化', 'min'), b('max', '最大化', 'max'), b('close', '关闭', 'x', 'close'));
  }

  let compact = false;
  async function setCompact(on) {
    compact = on;
    RM.open = '';
    document.body.classList.toggle('compact', on);
    refresh();
    const resized = await winAction(on ? 'compact' : 'full');
    if (on && !resized) toast(DESK.ok ? '没能缩小窗口，先切成了窄条布局' : '这里只切换成窄条布局，窗口大小不变（用新版桌面壳打开会贴到屏幕右侧）');
    if (on) {
      pollLive(true);
      loadScreen();
    }
    requestAnimationFrame(() => {
      if (on) miniBox.scrollTop = miniBox.scrollHeight;
      else if (LIVE.stick) liveBox.scrollTop = liveBox.scrollHeight;
    });
  }

  // ---------- 页面切换：地址栏 #/run 这样记住当前页，刷新后还在这一页 ----------
  const PAGES = [
    ['run', '运行', 'activity', '启动后先跑已到期的任务，然后常驻，每天刷新后自动再跑一遍'],
    ['route', '每天的路线', 'route', '按顺序一项一项做：开关决定今天做不做，点开一项看它怎么做、改细节'],
    ['events', '活动', 'flag', '限时活动的任务放这里，和每天的路线分开'],
    ['tools', '工具', 'tool', '只在你点的时候跑一次的功能，不进每天的调度'],
    ['logs', '日志', 'file', '脚本每一步都记在这里，出错时自动保存最近 10 张截图'],
    ['settings', '设置', 'gear', '什么时候跑、出事怎么提醒你、连哪台模拟器，一般设一次就不用再动'],
  ];
  const pageFromHash = () => {
    const p = location.hash.replace(/^#\/?/, '');
    return PAGES.some((x) => x[0] === p) ? p : 'run';
  };
  let page = pageFromHash();
  const pageInfo = () => PAGES.find((x) => x[0] === page);

  function go(p) {
    if (pageFromHash() !== p) location.hash = '#/' + p;
    else if (page !== p) showPage(p);
  }

  function showPage(p) {
    page = p;
    RM.open = '';
    refresh();
    if (p === 'logs') loadLogs();
    if (p === 'run') {
      pollLive(true);
      loadScreen();
      requestAnimationFrame(() => { if (LIVE.stick) liveBox.scrollTop = liveBox.scrollHeight; });
    }
  }
  window.addEventListener('hashchange', () => { if (S) showPage(pageFromHash()); });

  // ---------- 和 gui.py 通信 ----------
  async function post(url, body) {
    try {
      const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Zjcs': '1' }, body: JSON.stringify(body || {}) });
      const data = await res.json().catch(() => ({}));
      return { ok: res.ok, status: res.status, data };
    } catch (e) {
      toast('连不上配置服务，看看 gui.py 是不是关了', 'error');
      return { ok: false, status: 0, data: {} };
    }
  }

  // ---------- 时间小工具 ----------
  const pad2 = (n) => String(n).padStart(2, '0');
  const hm = (d) => pad2(d.getHours()) + ':' + pad2(d.getMinutes());
  const hms = (d) => hm(d) + ':' + pad2(d.getSeconds());
  const dayStart = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  function dayLabel(d) {
    const diff = Math.round((dayStart(d) - dayStart(new Date())) / 86400000);
    if (diff === 0) return '今天';
    if (diff === 1) return '明天';
    if (diff === -1) return '昨天';
    return (d.getMonth() + 1) + '月' + d.getDate() + '日';
  }
  const when = (iso) => { const d = new Date(iso); return dayLabel(d) + ' ' + hm(d); };
  const shortWhen = (iso) => { const d = new Date(iso); const l = dayLabel(d); return l === '今天' ? hm(d) : l === '明天' ? '明天 ' + hm(d) : l; };
  function clock(ms) {
    const s = Math.max(0, Math.floor(ms / 1000));
    const m = Math.floor(s / 60);
    return m >= 60 ? Math.floor(m / 60) + ':' + pad2(m % 60) + ':' + pad2(s % 60) : m + ':' + pad2(s % 60);
  }
  function spanText(ms) {
    const s = Math.max(0, Math.round(ms / 1000));
    if (s < 60) return s + ' 秒';
    const m = Math.round(s / 60);
    return m < 60 ? m + ' 分钟' : Math.floor(m / 60) + ' 小时 ' + (m % 60) + ' 分';
  }
  const RESULT = { success: ['完成', 'ok'], skip: ['跳过', 'mute'], failed: ['失败', 'bad'], error: ['出错', 'bad'], human: ['停下', 'bad'] };
  const EXIT = { done: '到期的任务都跑完了', empty: '没有开着的任务', task: '单独跑的任务结束了', stopped: '按了停止', human: '需要你处理', error: '脚本出错', killed: '进程意外结束' };

  function emptyEl(ic, title, sub) {
    return h('div', { class: 'empty' }, icon(ic, 36), h('b', null, title), sub ? h('span', null, sub) : null);
  }

  // 级别图标：日志行和提示条共用
  const LV_SVG = {
    ok: '<path d="M4.2 8.3l2.5 2.5 5-5.1" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
    warn: '<path d="M8 4.2v4.6M8 11.6h.01" stroke="#fff" stroke-width="2" stroke-linecap="round" fill="none"/>',
    err: '<path d="M5.2 5.2l5.6 5.6M10.8 5.2l-5.6 5.6" stroke="#fff" stroke-width="2" stroke-linecap="round" fill="none"/>',
    start: '<path d="M5 3.6v8.8l7-4.4z" fill="#fff"/>',
  };
  function lvIcon(lv, title) {
    const el = h('span', { class: 'lvi ' + lv, title: title || null });
    if (LV_SVG[lv]) el.innerHTML = '<svg viewBox="0 0 16 16" aria-hidden="true">' + LV_SVG[lv] + '</svg>';
    return el;
  }

  // ---------- 运行状态 ----------
  const R = { status: null, busy: '', lastAlive: null, confirm: new Map(), offline: false };
  const RM = { open: '' };   // 运行按钮旁的下拉菜单开在哪个按钮上
  const nameOf = (task) => (S.arg[task] && S.arg[task]._name) || task;

  function runState() {
    const st = R.status;
    if (!st) return { kind: 'unknown' };
    const rt = st.runtime;
    if (rt.alive) {
      if (rt.stopping || st.stop_pending) return { kind: 'stopping', task: rt.task, since: rt.task ? rt.task_started : '' };
      if (rt.state === 'running' && rt.task) return { kind: 'running', task: rt.task, since: rt.task_started };
      if (rt.state === 'waiting') return { kind: 'waiting', next: rt.next_run };
      return { kind: 'starting' };
    }
    return { kind: 'stopped', exit: rt.exit, message: rt.message, ended: rt.ended };
  }

  /** 状态胶囊、侧栏徽标、状态说明都从这里取 */
  function runInfo() {
    const s = runState();
    if (R.offline) return { pill: '连不上', cls: 'bad', badge: '连不上', meta: '连不上配置服务，看看 gui.py 是不是关了' };
    if (s.kind === 'running') return { pill: '正在跑', cls: 'live', badge: '运行中', meta: '当前：' + nameOf(s.task) + (s.since ? ' · ' + hm(new Date(s.since)) + ' 开始' : '') };
    if (s.kind === 'starting') return { pill: '正在启动', cls: 'live', badge: '运行中', meta: '正在连接模拟器…' };
    if (s.kind === 'waiting') return { pill: '等下一次', cls: 'wait', badge: '等待中', meta: s.next ? '下一次：' + when(s.next) : '常驻中，到点自动继续' };
    if (s.kind === 'stopping') return { pill: '正在停止', cls: 'warn', badge: '停止中', meta: s.task ? '做完「' + nameOf(s.task) + '」就停' : '马上停止' };
    if (s.kind === 'stopped') {
      const bad = ['human', 'error', 'killed'].includes(s.exit);
      const end = s.ended ? when(s.ended) + ' ' : '';
      return { pill: bad ? '停下了' : '没在运行', cls: bad ? 'bad' : 'idle', badge: bad ? '停下了' : '', bad, meta: s.exit ? end + (bad ? '停下：' : '结束：') + (s.message || EXIT[s.exit]) : '还没启动过' };
    }
    return { pill: '读取中', cls: 'idle', badge: '', meta: '正在读取运行状态…' };
  }

  /** 状态下面那段说明：现在在做什么、点按钮会怎样 */
  function runDetail() {
    const s = runState();
    if (R.offline) return '配置服务没有响应。确认 gui.py 正在运行；脚本本身不受影响，照常在后台跑。';
    if (s.kind === 'running') return '做完会接着跑排队中的任务。停止会等这一项做完，不会卡在买到一半、打到一半。';
    if (s.kind === 'waiting') return '今天到期的都跑完了。脚本开着，到点会自己继续；这期间点「立即执行」会马上跑。';
    if (s.kind === 'stopping') return '当前任务做完就停。等不及可以强制停止，正在做的任务会中断，下次从主界面重新进入。';
    if (s.kind === 'starting') return '正在连接模拟器…';
    if (s.kind === 'stopped' && ['human', 'error', 'killed'].includes(s.exit)) return (s.message || EXIT[s.exit]) + '。处理好之后点「启动」继续；出错前的截图在「日志 → 错误截图」。';
    return '点「启动」会先跑已到期的任务，然后常驻等下一次刷新。关掉这个窗口，脚本照样在后台跑。';
  }

  const todayCounts = () => {
    const hs = (R.status && R.status.history) || [];
    return {
      success: hs.filter((r) => r.result === 'success').length,
      skip: hs.filter((r) => r.result === 'skip').length,
      failed: hs.filter((r) => ['failed', 'error', 'human'].includes(r.result)).length,
    };
  };

  async function pollStatus() {
    try {
      const res = await fetch('/api/status', { cache: 'no-store' });
      if (!res.ok) throw new Error(String(res.status));
      R.status = await res.json();
      R.offline = false;
    } catch (e) {
      R.offline = true;
    }
    const alive = !!(R.status && R.status.runtime.alive);
    if (R.lastAlive === true && !alive && !R.offline) {
      const s = runState();
      if (s.exit === 'human' || s.exit === 'error') toast('停下了：' + (s.message || EXIT[s.exit]), 'error');
      else toast('已停止：' + (EXIT[s.exit] || '已停止'));
    }
    if (!R.offline) R.lastAlive = R.status ? alive : R.lastAlive;
    refresh();
  }

  async function startRun() {
    if (R.busy) return;
    R.busy = 'start';
    refresh();
    const r = await post('/api/run/start');
    R.busy = '';
    if (r.ok) toast(D.changes > 0 ? '已启动。还有没保存的改动，脚本用的是已保存的设置' : '已启动，到期的任务马上开始跑', D.changes > 0 ? 'error' : 'ok');
    else if (r.status) toast(r.data.error || '启动失败', 'error');
    await pollStatus();
  }

  async function stopRun(force) {
    if (R.busy) return;
    R.busy = force ? 'force' : 'stop';
    refresh();
    const r = await post('/api/run/stop', { force: !!force });
    R.busy = '';
    if (r.ok) toast(force ? '已强制停止' : runState().kind === 'running' ? '当前任务做完就停' : '马上停止');
    else if (r.status) toast(r.data.error || '停止失败', 'error');
    await pollStatus();
  }

  const ranToday = (t) => t.last_run && t.result === 'success' && dayStart(new Date(t.last_run)) === dayStart(new Date());

  async function runNow(t) {
    if (t.run_now) return;
    // 今天已经成功跑过的再跑一次，可能会再花晨星，要多点一下确认
    const c = R.confirm.get(t.task);
    if (ranToday(t) && !(c && Date.now() - c < 4000)) {
      R.confirm.set(t.task, Date.now());
      refresh();
      setTimeout(refresh, 4100);
      return;
    }
    R.confirm.delete(t.task);
    const s = runState();
    const r = await post('/api/run/task', { task: t.task });
    if (r.ok) {
      if (r.data.started) toast('已启动脚本，先跑「' + t.name + '」，接着跑其他到期的任务');
      else if (s.kind === 'running') toast('「' + nameOf(s.task) + '」做完就跑「' + t.name + '」');
      else toast('马上开始跑「' + t.name + '」');
    } else if (r.status) {
      toast(r.data.error || '没能加入队列', 'error');
    }
    await pollStatus();
  }

  // ---------- 运行按钮：启动 / 做完这项就停（下拉里有强制停止）/ 强制停止 ----------
  function runMode() {
    if (R.offline) return 'off';
    const k = runState().kind;
    // 命令行 --task 单独跑的任务不接收停止指令，只给强制停止
    const single = !!(R.status && R.status.runtime.alive && R.status.runtime.mode === 'task');
    if (k === 'stopped' || k === 'unknown') return 'start';
    if (k === 'stopping' || single) return 'force';
    return 'stop';
  }

  function runButton(where, extraClass = '') {
    const mode = () => runMode();
    const text = () => {
      if (R.busy === 'start') return '正在启动…';
      if (R.busy === 'stop') return '正在停止…';
      if (R.busy === 'force') return '正在结束…';
      const m = mode();
      if (m === 'start') return '启动';
      if (m === 'force') return '强制停止';
      if (m === 'off') return '连不上配置服务';
      return runState().kind === 'running' ? '做完这项就停' : '停止';
    };
    const main = () => {
      const m = mode();
      if (m === 'start') startRun();
      else if (m === 'stop') stopRun(false);
      else if (m === 'force') stopRun(true);
    };
    const cls = { start: '', stop: ' stop has-drop', force: ' stop', off: ' off' };
    return h('div', { class: () => 'split-btn ' + extraClass + cls[mode()] + (R.busy ? ' busy' : '') },
      h('button', {
        type: 'button',
        class: 'sb-main',
        onclick: main,
        title: () => ({ start: '先跑已到期的任务，然后常驻等下一次刷新', stop: '当前任务做完再停，不会卡在买到一半、打到一半', force: '马上结束脚本进程，正在做的任务会中断', off: '' }[mode()]),
      },
      h('span', { class: 'spinner', 'aria-hidden': 'true', show: () => !!R.busy }),
      h('span', { show: () => !R.busy && mode() === 'start', style: { display: 'contents' } }, icon('play', 16)),
      h('span', { show: () => !R.busy && mode() === 'stop', style: { display: 'contents' } }, icon('stop', 16)),
      h('span', { show: () => !R.busy && mode() === 'force', style: { display: 'contents' } }, icon('x', 16)),
      h('span', null, text)),
      h('button', {
        type: 'button',
        class: 'sb-drop',
        show: () => mode() === 'stop',
        title: '更多停止方式',
        'aria-label': '更多停止方式',
        'aria-expanded': () => String(RM.open === where),
        onclick: (e) => { e.stopPropagation(); RM.open = RM.open === where ? '' : where; refresh(); },
      }, icon('chev', 16)),
      h('div', { class: 'menu up', show: () => RM.open === where && mode() === 'stop' },
        h('button', { type: 'button', class: 'danger', onclick: () => { RM.open = ''; stopRun(true); } },
          icon('x', 16), h('span', { class: 'mi' }, '强制停止', h('small', null, '马上结束进程，正在做的任务会中断')))));
  }
  document.addEventListener('click', () => { if (RM.open) { RM.open = ''; refresh(); } });

  // ---------- 模拟器画面：运行页和迷你模式每 3 秒截一张，其他时候 30 秒一张（侧栏的连接状态用） ----------
  const SCREEN_KEY = 'zjcs.gui.screen';
  const SC = { auto: true, url: '', time: null, error: '', busy: false, size: '' };
  try { SC.auto = localStorage.getItem(SCREEN_KEY) !== 'off'; } catch (e) { /* 默认开 */ }

  async function loadScreen() {
    if (SC.busy) return;
    SC.busy = true;
    refresh();
    try {
      const res = await fetch('/api/screenshot?t=' + Date.now(), { cache: 'no-store' });
      if (res.ok) {
        const url = URL.createObjectURL(await res.blob());
        if (SC.url) URL.revokeObjectURL(SC.url);
        SC.url = url;
        SC.error = '';
        SC.time = new Date();
      } else {
        SC.error = (await res.json().catch(() => ({}))).error || '截图失败';
      }
    } catch (e) {
      SC.error = '连不上配置服务';
    } finally {
      SC.busy = false;
      refresh();
    }
  }

  function setScreenAuto() {
    SC.auto = !SC.auto;
    try { localStorage.setItem(SCREEN_KEY, SC.auto ? 'on' : 'off'); } catch (e) { /* 不记 */ }
    if (SC.auto) loadScreen();
    refresh();
  }

  function screenView() {
    return h('div', { class: 'screen' },
      h('img', { src: () => SC.url || null, alt: '模拟器当前画面', show: () => !!SC.url, onload: (e) => { SC.size = e.target.naturalWidth + '×' + e.target.naturalHeight; } }),
      h('div', { class: 'screen-empty', show: () => !SC.url }, icon('image', 22), h('span', null, () => (SC.error ? '截不到图' : '正在截图…'))),
      h('button', { type: 'button', class: () => 'screen-btn' + (SC.busy ? ' spinning' : ''), title: '现在刷新画面', 'aria-label': '现在刷新画面', onclick: loadScreen }, icon('refresh', 14)));
  }

  /** 模拟器连接状态：[色调, 文字]，侧栏卡片、运行按钮下的提示、迷你模式底栏共用 */
  function deviceState() {
    if (SC.url && !SC.error) return ['ok', '已连接 · ' + (SC.size || '画面正常') + (SC.time ? ' · ' + hms(SC.time) : '')];
    if (SC.error) return ['bad', '截不到图：' + SC.error];
    return ['', '正在检测…'];
  }

  function connCard() {
    return h('button', {
      type: 'button',
      class: () => 'conn ' + deviceState()[0],
      title: () => (S ? '设备 ' + get('Device', 'Serial') + '。' : '') + deviceState()[1] + '\n点一下去设置里检查连接',
      onclick: () => jumpTo('Device'),
    }, h('span', { class: 'conn-ic' }, icon('device', 18)),
    h('span', { class: 'conn-text' }, h('b', null, '模拟器'), h('small', null, () => deviceState()[1])));
  }

  function footHint() {
    const hint = () => {
      const s = runState();
      if (R.offline) return ['bad', '连不上配置服务'];
      if (s.kind === 'running') return ['run', '正在跑「' + nameOf(s.task) + '」· 停止会等这一项做完'];
      if (s.kind === 'starting') return ['run', '正在启动脚本…'];
      if (s.kind === 'waiting') return ['ok', '常驻中 · 到点自动继续，关掉窗口也照样跑'];
      if (s.kind === 'stopping') return ['warn', '当前任务做完就停'];
      const [tone, text] = deviceState();
      return [tone, '模拟器' + (tone === 'ok' ? '已连接 · ' + get('Device', 'Serial') : tone === 'bad' ? text : '：正在检测…')];
    };
    return h('div', { class: () => 'foot-hint ' + hint()[0] }, h('span', { class: 'dot' }), h('span', { title: () => hint()[1] }, () => hint()[1]));
  }

  // ---------- 实时日志：每 1.5 秒从上次读到的位置接着读，运行页和迷你模式各一份 ----------
  const LIVE = { offset: -1, date: '', busy: false, stick: true, level: 'all', kw: '' };
  const MINI = { onlyWarn: false };
  const LINE_RE = /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\.\d{3} \| (\w+)\s*\| ?(.*)$/;
  const LEVEL = { WARNING: ['警告', 'warn'], ERROR: ['错误', 'err'], CRITICAL: ['严重', 'err'] };
  const UPPER = () => {
    const map = {};
    if (S) Object.keys(S.arg).forEach((g) => { map[g.toUpperCase()] = nameOf(g); });
    return map;
  };

  function logLines(text) {
    const out = [];
    text.split('\n').forEach((line) => {
      const m = LINE_RE.exec(line);
      if (m) out.push({ time: m[2], level: m[3], msg: m[4] });
      else if (out.length) out[out.length - 1].msg += '\n' + line;
      else if (line) out.push({ time: '', level: 'INFO', msg: line });
    });
    return out;
  }

  /** 一行日志：任务开头（==== TASK ====）蓝色高亮，任务结果绿/红高亮，小节标题加粗 */
  let upperCache = null;
  function lineEl(e) {
    const [label, lv] = LEVEL[e.level] || ['', 'info'];
    let cls = lv;
    let text = e.msg;
    let ic = lv;
    if (/^={6,}/.test(text)) {
      const name = text.replace(/[=\s]+/g, ' ').trim();
      if (!name) return null;
      upperCache = upperCache || UPPER();
      text = '开始：' + (upperCache[name] || name);
      cls += ' start';
      ic = 'start';
    } else if (/^-{6,}/.test(text)) {
      text = text.replace(/^[-\s]+|[-\s]+$/g, '');
      cls += ' sub';
    } else {
      const m = /^任务 (\w+) 结果: (\w+)$/.exec(text);
      if (m) {
        const [rl, rc] = RESULT[m[2]] || [m[2], 'mute'];
        text = '「' + nameOf(m[1]) + '」' + rl;
        if (rc === 'ok') { cls = 'ok hl'; ic = 'ok'; }
        if (rc === 'bad') { cls = 'err hl'; ic = 'err'; }
      }
    }
    return h('div', { class: 'lrow ' + cls }, h('time', null, e.time), lvIcon(ic, label), h('div', { class: 'msg' }, text));
  }

  function rowVisible(el, level, kw) {
    const isWarn = el.classList.contains('warn') || el.classList.contains('err');
    const okLevel = level === 'all' || (level === 'warn' ? isWarn : el.classList.contains('err'));
    return okLevel && (!kw || el.textContent.toLowerCase().includes(kw));
  }

  function filterBox(box, level, kw) {
    let shown = 0;
    [...box.children].forEach((el) => {
      const ok = rowVisible(el, level, kw);
      el.hidden = !ok;
      if (ok) shown += 1;
    });
    return shown;
  }

  function appendLog(box, items, max, stick, keep) {
    const frag = document.createDocumentFragment();
    items.map(lineEl).filter(Boolean).forEach((el) => {
      if (keep && !keep(el)) el.hidden = true;
      frag.appendChild(el);
    });
    box.appendChild(frag);
    while (box.childElementCount > max) box.firstElementChild.remove();
    if (stick) box.scrollTop = box.scrollHeight;
  }

  const liveBox = h('div', { class: 'log', role: 'log', 'aria-live': 'off', 'data-empty': '今天还没有日志。点「启动」后，脚本的每一步都会实时显示在这里。' });
  const miniBox = h('div', { class: 'mini-log log', role: 'log', 'aria-live': 'off', 'data-empty': '还没有日志' });
  liveBox.addEventListener('scroll', () => {
    const stick = liveBox.scrollHeight - liveBox.scrollTop - liveBox.clientHeight < 40;
    // 只有「回到最新」按钮要变的时候才刷新，滚轮一格会触发很多次 scroll
    if (stick === LIVE.stick) return;
    LIVE.stick = stick;
    refresh();
  }, { passive: true });

  const liveOn = () => (page === 'run' || compact) && !document.hidden;

  async function pollLive(force) {
    if (LIVE.busy || (!force && !liveOn())) return;
    const d = new Date();
    const today = d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
    if (today !== LIVE.date) { LIVE.date = today; LIVE.offset = -1; }
    LIVE.busy = true;
    try {
      const res = await fetch('/api/log?date=' + LIVE.date + '&offset=' + LIVE.offset + '&tail=400', { cache: 'no-store' });
      const body = await res.json();
      if (body.reset) { liveBox.replaceChildren(); miniBox.replaceChildren(); }
      LIVE.offset = body.offset;
      if (body.text) {
        const items = logLines(body.text);
        const kw = LIVE.kw.trim().toLowerCase();
        appendLog(liveBox, items, 1500, LIVE.stick, (el) => rowVisible(el, LIVE.level, kw));
        const miniAt = miniBox.scrollHeight - miniBox.scrollTop - miniBox.clientHeight < 40;
        appendLog(miniBox, items, 300, miniAt, (el) => rowVisible(el, MINI.onlyWarn ? 'warn' : 'all', ''));
      }
    } catch (e) { /* 下一轮再试 */ } finally {
      LIVE.busy = false;
    }
  }

  function levelSelect(read, write) {
    const sel = h('select', { class: 'input', 'aria-label': '按级别筛选', onchange: (e) => write(e.target.value) },
      h('option', { value: 'all' }, '全部级别'), h('option', { value: 'warn' }, '警告以上'), h('option', { value: 'err' }, '只看错误'));
    bindings.push(() => { if (sel.value !== read()) sel.value = read(); });
    return sel;
  }

  function searchBox(placeholder, onInput) {
    let timer = 0;
    return h('label', { class: 'search-input' }, icon('search', 15),
      h('input', { type: 'search', placeholder, spellcheck: 'false', 'aria-label': placeholder, oninput: (e) => { clearTimeout(timer); const v = e.target.value; timer = setTimeout(() => onInput(v), 150); } }));
  }

  // ---------- 任务队列 ----------
  function queueModel() {
    const st = R.status;
    const now = new Date(st.now);
    const running = st.runtime.alive ? st.runtime.task : null;
    const rest = st.tasks.filter((t) => t.task !== running);
    const first = rest.filter((t) => t.run_now).sort((a, b) => String(a.run_now).localeCompare(String(b.run_now)));
    const due = rest.filter((t) => t.enabled && !t.run_now && (!t.next_run || new Date(t.next_run) <= now));
    const waiting = rest.filter((t) => t.enabled && !t.run_now && t.next_run && new Date(t.next_run) > now)
      .sort((a, b) => new Date(a.next_run) - new Date(b.next_run));
    const off = rest.filter((t) => !t.enabled && !t.run_now);
    return { running: running ? st.tasks.find((t) => t.task === running) || { task: running, name: nameOf(running) } : null, queue: first.concat(due), waiting, off, now };
  }

  function lastResultEl(t) {
    if (!t.last_run) return h('span', { class: 'hint' }, '还没跑过');
    const [label, cls] = RESULT[t.result] || ['跑过', 'mute'];
    const fail = t.result === 'failed' && t.failure ? '（连续 ' + t.failure + ' 次）' : '';
    return h('span', { title: when(t.last_run) + ' ' + label + fail }, h('em', { class: 'status sm ' + cls }, label + fail), ' ' + when(t.last_run));
  }

  function runNowButton(t, kind) {
    if (t.run_now) return h('span', { class: 'tag' }, '已插队');
    const c = R.confirm.get(t.task);
    const confirming = c && Date.now() - c < 4000;
    return h('button', {
      type: 'button',
      class: 'btn btn-sm' + (confirming ? ' confirm' : ''),
      onclick: () => runNow(t),
      title: confirming ? '今天已经成功跑过，再跑可能会再花晨星' : kind === 'off' ? '开关没开也可以先跑一次试试' : '插到队首，当前任务做完马上跑',
    }, icon('play', 11), confirming ? '再点一次确认' : kind === 'off' ? '试跑一次' : '立即执行');
  }

  function queueRow(t, kind) {
    const alive = R.status.runtime.alive;
    let meta;
    if (kind === 'running') meta = h('span', null, '已经跑了 ', h('b', { class: 'num', 'data-since': R.status.runtime.task_started || '' }));
    else if (kind === 'queue') meta = t.run_now ? (alive ? '当前任务做完就跑' : '等脚本启动') : alive ? '排队中' : '已到期，启动后就跑';
    else if (kind === 'waiting') meta = when(t.next_run) + ' 跑';
    else meta = '开关没开';
    return h('div', { class: 'grow-r ' + kind },
      h('span', { class: 't-main' }, t.name),
      typeof meta === 'string' ? h('span', null, meta) : meta,
      lastResultEl(t),
      kind === 'running' ? h('span', { class: 'pulse', 'aria-hidden': 'true' }) : h('span', { class: 'acts' }, runNowButton(t, kind)));
  }

  const QOFF = { open: false };
  function queueTable() {
    const body = h('div', { class: 'gtbody' });
    let sig = '';
    bindings.push(() => {
      if (!R.status) return;
      const m = queueModel();
      const next = JSON.stringify([m.running, m.queue, m.waiting, m.off, [...R.confirm.entries()].filter(([, v]) => Date.now() - v < 4000), Math.floor(Date.now() / 60000), R.status.runtime.alive]);
      if (next === sig) return;
      sig = next;
      const sec = (title, n) => h('div', { class: 'gsec' }, h('span', null, title), h('span', { class: 'count' }, String(n)));
      const groups = [];
      m.waiting.forEach((t) => {
        const label = dayLabel(new Date(t.next_run));
        if (!groups.length || groups[groups.length - 1][0] !== label) groups.push([label, []]);
        groups[groups.length - 1][1].push(t);
      });
      const alive = R.status.runtime.alive;
      body.replaceChildren(...[
        m.running ? [sec('正在跑', 1), queueRow(m.running, 'running')] : [],
        sec(alive ? '排队中' : '已到期', m.queue.length),
        m.queue.length ? m.queue.map((t) => queueRow(t, 'queue')) : h('div', { class: 'empty sm' }, h('span', null, alive ? '没有排队的任务' : '没有到期的任务')),
        groups.map(([label, list]) => [sec(label === '今天' ? '今天晚些时候' : label, list.length), list.map((t) => queueRow(t, 'waiting'))]),
        m.off.length ? h('details', { class: 'gfold', open: QOFF.open, ontoggle: (e) => { QOFF.open = e.target.open; } },
          h('summary', { class: 'gsec' }, h('span', null, '没开的任务'), h('span', { class: 'count' }, String(m.off.length)), icon('chev', 14, 'chev')),
          m.off.map((t) => queueRow(t, 'off'))) : null,
      ].flat(Infinity).filter(Boolean));
      tickSince();
    });
    return h('div', { class: 'gtable queue-table' },
      h('div', { class: 'gthead' }, h('span', null, '任务'), h('span', null, '状态'), h('span', null, '上次'), h('span', { class: 'r' }, '操作')),
      body);
  }

  /** 控制台里的小队列：最近做完的两项、正在跑的、接下来的几项 */
  function stepsList() {
    const list = h('ol', { class: 'steps', 'aria-label': '任务进度' });
    let sig = '';
    bindings.push(() => {
      if (!R.status) return;
      const m = queueModel();
      const hs = (R.status.history || []).filter((r) => !m.running || r.task !== m.running.task);
      const seen = new Set();
      const done = [];
      hs.forEach((r) => { if (!seen.has(r.task) && done.length < 2) { seen.add(r.task); done.unshift(r); } });
      const rows = done.map((r) => ({ name: nameOf(r.task), cls: r.result === 'success' ? 'done' : r.result === 'skip' ? 'skip' : 'fail', em: hm(new Date(r.end)) }));
      if (m.running) rows.push({ name: m.running.name, cls: 'cur', since: R.status.runtime.task_started || '' });
      const next = m.queue.concat(m.waiting);
      const room = Math.max(0, 8 - rows.length);
      next.slice(0, room).forEach((t) => rows.push({
        name: t.name,
        cls: '',
        em: t.run_now ? '插队' : (!t.next_run || new Date(t.next_run) <= m.now) ? '已到期' : shortWhen(t.next_run),
      }));
      const more = next.length - room;
      const s = JSON.stringify([rows, more]);
      if (s === sig) return;
      sig = s;
      const items = rows.map((r) => h('li', { class: r.cls }, h('span', null, r.name), r.since !== undefined ? h('em', { 'data-since': r.since }) : h('em', null, r.em)));
      if (more > 0) items.push(h('li', { class: 'more' }, h('button', { type: 'button', onclick: () => { RT.tab = 'queue'; refresh(); } }, '还有 ' + more + ' 项 · 看队列')));
      if (!rows.length) items.push(h('li', { class: 'more' }, R.status.tasks.some((t) => t.enabled) ? '今天开着的任务都跑完了' : '没有开着的任务'));
      list.replaceChildren(...items);
      tickSince();
    });
    return list;
  }

  // ---------- 运行记录 ----------
  function histRow(r, onError) {
    const start = new Date(r.start);
    const [text, cls] = RESULT[r.result] || [r.result, 'mute'];
    return h('div', { class: 'grow-r' },
      h('span', { class: 't-num' }, hm(start) + ' – ' + hm(new Date(r.end))),
      h('span', { class: 't-main' }, nameOf(r.task)),
      h('span', { class: 't-num' }, spanText(new Date(r.end) - start)),
      h('span', null, h('em', { class: 'status sm ' + cls }, text)),
      h('span', { class: 'acts' }, r.error ? h('button', { type: 'button', class: 'btn btn-sm btn-ghost', onclick: () => onError(r.error) }, icon('image', 13), '错误截图') : null));
  }

  const histHead = () => h('div', { class: 'gthead' }, h('span', null, '时间'), h('span', null, '任务'), h('span', null, '耗时'), h('span', null, '结果'), h('span', { class: 'r' }, '截图'));

  function todayTable() {
    const body = h('div', { class: 'gtbody' });
    let sig = '';
    bindings.push(() => {
      const hs = (R.status && R.status.history) || [];
      const s = JSON.stringify(hs);
      if (s === sig) return;
      sig = s;
      body.replaceChildren(...(hs.length ? hs.map((r) => histRow(r, openErrorShots)) : [emptyEl('inbox', '今天还没有运行记录', '每跑完一项都会记在这里')]));
    });
    return h('div', { class: 'gtable hist-table' }, histHead(), body);
  }

  function openErrorShots(name) {
    LG.tab = 'errors';
    LG.folder = name;
    if (page === 'logs') {
      renderErrors();
      refresh();
    } else {
      go('logs');
    }
  }

  // ---------- 运行页：左边控制台，右边日志 / 队列 / 今天的记录 ----------
  const RT = { tab: 'log' };

  function tabbar(read, write, tabs, side) {
    return h('div', { class: 'tabbar', role: 'tablist' },
      tabs.map(([id, label, count]) => h('button', { type: 'button', role: 'tab', class: 'tab', 'aria-selected': () => String(read() === id), onclick: () => write(id) },
        label, count ? h('em', { class: 'count' }, count) : null)),
      side ? h('div', { class: 'tabbar-side' }, side) : null);
  }

  function statNum(key, label, cls) {
    return h('div', { class: () => 'stat ' + (todayCounts()[key] ? cls : 'zero') }, h('b', null, () => String(todayCounts()[key])), h('span', null, label));
  }

  function runPage() {
    const running = () => !!runState().since;
    const toLatest = h('button', { type: 'button', class: 'to-latest', show: () => !LIVE.stick, onclick: () => { LIVE.stick = true; liveBox.scrollTop = liveBox.scrollHeight; refresh(); } }, icon('down', 14), '回到最新');
    return h('section', { class: 'page page-split', show: () => page === 'run' },
      h('div', { class: 'console' },
        h('div', { class: 'console-body' },
          h('div', { class: 'block' },
            h('div', { class: 'status-row' },
              h('em', { class: () => 'status ' + runInfo().cls }, () => runInfo().pill),
              h('span', { class: 'grow' }),
              h('span', { class: () => 'timer' + (running() ? '' : ' dim'), 'data-since': () => runState().since || '', 'data-empty': '0:00' }, '0:00')),
            h('div', { class: 'status-meta', title: () => runInfo().meta }, () => runInfo().meta),
            h('div', { class: 'stats' }, statNum('success', '今天完成', 'ok'), statNum('skip', '今天跳过', ''), statNum('failed', '今天失败', 'bad'))),
          h('div', { class: 'block' },
            h('div', { class: 'live' }, screenView(), stepsList()),
            h('div', { class: 'screen-foot' },
              h('span', null, () => (SC.error && SC.url ? '最新一张没截到' : SC.time ? hms(SC.time) + ' 的画面' : '模拟器画面')),
              h('span', { class: 'grow' }),
              h('button', { type: 'button', role: 'switch', class: 'mini-switch', 'aria-checked': () => String(SC.auto), onclick: setScreenAuto }, h('span', { class: 'switch' }), '自动刷新')),
            h('div', { class: () => 'caption' + (runInfo().bad || R.offline ? ' error' : runState().kind === 'stopping' ? ' warn' : '') }, h('span', null, runDetail))),
          h('div', { class: 'block' },
            h('div', { class: 'block-head' }, h('h3', null, '运行设置'), h('a', { class: 'link-btn', href: '#/settings', style: { 'margin-left': 'auto', 'font-size': '12px' } }, '去设置', icon('arrow', 13))),
            h('div', { class: 'kv' },
              h('div', null, h('label', null, '每天开始'), h('span', { class: 'v' }, h('b', null, () => localTime(get('Scheduler', 'ServerUpdate'), get('Scheduler', 'ServerTimezone'))), ' 你电脑上的时间')),
              h('div', null, h('label', null, '开着的'), h('span', { class: 'v' }, h('b', null, () => D.enabled + ' / ' + D.tasks), ' 项 · ', h('a', { class: 'link-btn', href: '#/route' }, '改路线'))),
              h('div', null, h('label', null, '最多花'), h('span', { class: 'v' }, h('b', { class: 'gold' }, () => fmt(D.total) + (D.more ? '+' : '')), ' 晨星 / 天')),
              h('div', null, h('label', null, '失败上限'), h('span', { class: 'v' }, '同一项连续 ', h('b', null, () => String(get('Scheduler', 'FailureLimit'))), ' 次就停下等你'))))),
        h('div', { class: 'console-foot' }, runButton('main'), footHint())),
      h('div', { class: 'work' },
        tabbar(() => RT.tab, (id) => {
          RT.tab = id;
          refresh();
          if (id === 'log' && LIVE.stick) requestAnimationFrame(() => { liveBox.scrollTop = liveBox.scrollHeight; });
        }, [
          ['log', '实时日志'],
          ['queue', '任务队列', () => (R.status ? String(queueModel().queue.length + (queueModel().running ? 1 : 0)) : '0')],
          ['today', '今天的记录', () => String(((R.status && R.status.history) || []).length)],
        ]),
        h('div', { class: 'tab-panel', show: () => RT.tab === 'log' },
          h('div', { class: 'toolbar' },
            searchBox('搜索日志，例如 公会战、失败', (v) => { LIVE.kw = v; filterBox(liveBox, LIVE.level, v.trim().toLowerCase()); }),
            levelSelect(() => LIVE.level, (v) => { LIVE.level = v; filterBox(liveBox, v, LIVE.kw.trim().toLowerCase()); }),
            h('span', { class: 'grow' }),
            h('a', { class: 'btn btn-ghost', href: '#/logs' }, icon('logs', 15), '历史日志')),
          h('div', { class: 'log-wrap' }, liveBox, toLatest)),
        h('div', { class: 'tab-panel', show: () => RT.tab === 'queue' },
          h('div', { class: 'toolbar' },
            h('div', { class: 'meta' }, '按路线顺序跑', h('i', { class: 'vsep' }), '点「立即执行」插到队首，当前任务做完马上跑')),
          queueTable()),
        h('div', { class: 'tab-panel', show: () => RT.tab === 'today' },
          h('div', { class: 'toolbar' },
            h('div', { class: 'meta' }, '完成 ', h('b', null, () => String(todayCounts().success)), h('i', { class: 'vsep' }), '跳过 ', h('b', null, () => String(todayCounts().skip)), h('i', { class: 'vsep' }), '失败 ', h('b', null, () => String(todayCounts().failed))),
            h('span', { class: 'grow' }),
            h('a', { class: 'btn btn-ghost', href: '#/logs', onclick: () => { LG.tab = 'history'; } }, icon('clock', 15), '全部记录')),
          todayTable())));
  }

  // ---------- 日志页 ----------
  const LG = { tab: 'log', dates: [], date: '', errors: [], history: [], level: 'all', kw: '', folder: '', loading: false, shown: undefined };
  const logBox = h('div', { class: 'log', role: 'log', 'data-empty': '这一天没有日志' });
  const historyBody = h('div', { class: 'gtbody' });
  const errorList = h('div', { class: 'err-list' });
  const errorShots = h('div', { class: 'err-shots' });

  async function loadLogs() {
    try {
      const res = await fetch('/api/logs', { cache: 'no-store' });
      const body = await res.json();
      LG.dates = body.dates;
      LG.errors = body.errors;
      LG.history = body.history;
      if (!LG.date || !LG.dates.some((d) => d.date === LG.date)) LG.date = LG.dates.length ? LG.dates[0].date : '';
      if ((!LG.folder || !LG.errors.some((f) => f.name === LG.folder)) && LG.errors.length) LG.folder = LG.errors[0].name;
      renderHistory();
      renderErrors();
      refresh();
      await loadLogFile();
    } catch (e) {
      toast('读不到日志', 'error');
    }
  }

  async function loadLogFile() {
    if (!LG.date) {
      logBox.replaceChildren();
      LG.shown = 0;
      refresh();
      return;
    }
    LG.loading = true;
    refresh();
    try {
      const res = await fetch('/api/log?date=' + LG.date + '&tail=6000', { cache: 'no-store' });
      const body = await res.json();
      logBox.replaceChildren();
      appendLog(logBox, logLines(body.text), 6000, true, null);
      filterLog();
      logBox.scrollTop = logBox.scrollHeight;
    } finally {
      LG.loading = false;
      refresh();
    }
  }

  function filterLog() {
    LG.shown = filterBox(logBox, LG.level, LG.kw.trim().toLowerCase());
    refresh();
  }

  function errorTask(name) {
    // 错误截图目录名是保存的时间，在运行记录里找那段时间在跑的任务
    const m = /^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/.exec(name);
    if (!m) return null;
    const rec = LG.history.find((r) => r.error === name);
    if (rec) return nameOf(rec.task);
    const t = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]).getTime();
    const hit = LG.history.find((r) => new Date(r.start).getTime() <= t + 1000 && new Date(r.end).getTime() >= t - 1000);
    return hit ? nameOf(hit.task) : null;
  }

  const folderTime = (name) => name.replace(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/, '$2-$3 $4:$5:$6');

  function renderErrors() {
    errorList.replaceChildren(...(LG.errors.length ? LG.errors.map((f) => h('button', {
      type: 'button',
      class: 'err-item' + (f.name === LG.folder ? ' on' : ''),
      onclick: () => { LG.folder = f.name; renderErrors(); },
    }, h('b', null, folderTime(f.name)), h('span', null, (errorTask(f.name) ? errorTask(f.name) + ' · ' : '') + f.files.length + ' 张截图'))) : [h('div', { class: 'empty sm' }, h('span', null, '没有错误截图'))]));
    const folder = LG.errors.find((f) => f.name === LG.folder);
    errorShots.replaceChildren(...(folder ? folder.files.slice().reverse().map((file, i) => h('a', {
      class: 'shot', href: '/api/error/' + folder.name + '/' + file, target: '_blank', rel: 'noopener',
    }, h('img', { src: '/api/error/' + folder.name + '/' + file, alt: file, loading: 'lazy' }), h('span', null, (i === 0 ? '最后一张 · ' : '') + file.replace(/^(\d{2})(\d{2})(\d{2})_(\d+)\.png$/, '$1:$2:$3')))) : [emptyEl('image', '没有错误截图', '任务失败时会自动保存出错前的最近 10 张截图')]));
  }

  function renderHistory() {
    if (!LG.history.length) {
      historyBody.replaceChildren(emptyEl('inbox', '还没有运行记录', '每跑完一项都会记一笔'));
      return;
    }
    const rows = [];
    let day = '';
    LG.history.forEach((r) => {
      const label = dayLabel(new Date(r.start));
      if (label !== day) {
        day = label;
        rows.push(h('div', { class: 'gsec' }, label));
      }
      rows.push(histRow(r, openErrorShots));
    });
    historyBody.replaceChildren(...rows);
  }

  function logsPage() {
    const dateSel = h('select', { class: 'input', 'aria-label': '日期', onchange: (e) => { LG.date = e.target.value; loadLogFile(); } });
    let dateSig = '';
    bindings.push(() => {
      const sig = LG.dates.map((d) => d.date).join();
      if (sig !== dateSig) {
        dateSig = sig;
        dateSel.replaceChildren(...LG.dates.map((d) => h('option', { value: d.date }, dayLabel(new Date(d.date + 'T00:00:00')) + '（' + d.date + '）')));
      }
      if (dateSel.value !== LG.date) dateSel.value = LG.date;
    });
    return h('section', { class: 'page', show: () => page === 'logs' },
      h('div', { class: 'work' },
        tabbar(() => LG.tab, (id) => { LG.tab = id; refresh(); }, [
          ['log', '日志'],
          ['history', '运行记录', () => String(LG.history.length)],
          ['errors', '错误截图', () => String(LG.errors.length)],
        ], h('button', { type: 'button', class: 'btn btn-ghost', onclick: loadLogs }, icon('refresh', 15), '刷新')),
        h('div', { class: 'tab-panel', show: () => LG.tab === 'log' },
          h('div', { class: 'toolbar' },
            dateSel,
            levelSelect(() => LG.level, (v) => { LG.level = v; filterLog(); }),
            searchBox('搜索，例如 公会战、失败', (v) => { LG.kw = v; filterLog(); }),
            h('span', { class: 'grow' }),
            h('span', { class: 'hint' }, () => (LG.loading ? '读取中…' : (LG.shown === undefined ? '' : LG.shown + ' 条')))),
          h('div', { class: 'log-wrap' }, logBox)),
        h('div', { class: 'tab-panel', show: () => LG.tab === 'history' },
          h('div', { class: 'gtable hist-table', style: { 'padding-top': '12px' } }, histHead(), historyBody)),
        h('div', { class: 'tab-panel', show: () => LG.tab === 'errors' },
          h('div', { class: 'err-split' }, errorList, errorShots))));
  }

  // ---------- 活动、工具（占位） ----------
  function emptyPage(id, title, ic, lines) {
    return h('section', { class: 'page', show: () => page === id },
      h('div', { class: 'scroll' },
        h('div', { class: 'empty', style: { padding: '96px 24px' } }, icon(ic, 36), h('b', null, '还没有' + title), lines.map((t) => h('span', null, t)))));
  }

  // ---------- 每天的路线 ----------
  function routePage(groups) {
    const anyOpen = () => [...S.open].some((g) => has(g) && !isSetting(g));
    return h('section', { class: 'page', show: () => page === 'route' },
      h('div', { class: 'scroll' },
        h('div', { class: 'route' },
          h('div', { class: 'route-head' },
            h('span', { class: 'pill' }, () => D.enabled + ' / ' + D.tasks + ' 项开启'),
            h('span', null, '开关决定今天做不做；改完点右上角「保存」'),
            h('span', { class: 'grow' }),
            h('button', { type: 'button', class: 'btn btn-sm btn-ghost', show: anyOpen, onclick: () => { [...S.open].forEach((g) => { if (!isSetting(g)) S.open.delete(g); }); saveOpen(); refresh(); } }, '全部收起')),
          groups.map(([title, tasks], i) => routeGroup(i + 1, title, tasks, i === groups.length - 1)))),
      overview());
  }

  // ---------- 设置：每个分组直接展开 ----------
  function setGroup(g) {
    const spec = specOf(g);
    const name = S.arg[g]._name || g;
    const hasSwitch = 'Enable' in S.cfg[g];
    const on = () => !hasSwitch || isOn(g);
    const icons = { Scheduler: 'clock', Notify: 'bell', Device: 'device' };
    return h('div', { class: 'set-group', id: 'task-' + g },
      h('h2', null, icon(icons[g] || spec.icon || 'sliders', 16), name,
        h('span', { class: 'badge', show: () => changed(g) && !groupHasError(g) }, '已修改'),
        h('span', { class: 'badge error', show: () => groupHasError(g) }, '需要改一下'),
        hasSwitch ? h('button', { type: 'button', role: 'switch', 'aria-label': name, 'aria-checked': () => String(on()), onclick: () => set(g, 'Enable', !on()) },
          h('span', null, () => (on() ? '已开启' : '已关闭')), h('span', { class: 'switch' })) : null),
      h('p', null, () => (on() ? spec.sentence() : '已关闭')),
      h('div', { class: 'set-body' },
        spec.panel(),
        h('div', { class: 'reset-row', show: () => canReset(g) }, h('button', { type: 'button', class: 'btn btn-sm', onclick: () => reset(g) }, '恢复这一组的默认设置'))));
  }

  function settingsPage(ids) {
    const file = S.file ? S.file.split(/[\\/]/).slice(-2).join('/') : 'config/zjcs.yaml';
    return h('section', { class: 'page', show: () => page === 'settings' },
      h('div', { class: 'scroll settings' },
        h('div', { class: 'settings-inner' },
          ids.map(setGroup),
          h('div', { class: 'set-group' },
            h('h2', null, icon('sun', 16), '外观'),
            h('p', null, '跟随系统时，电脑切换深浅色这里跟着变。'),
            h('div', { class: 'set-row' }, h('div', { class: 'sr-text' }, h('b', null, '配色'), h('small', null, '只影响这个界面，不影响游戏和脚本')), h('div', { class: 'sr-ctl' }, themeSeg()))),
          h('div', { class: 'set-group' },
            h('h2', null, icon('dock', 16), '窗口'),
            h('div', { class: 'set-row' },
              h('div', { class: 'sr-text' }, h('b', null, '迷你模式'),
                h('small', null, DESK.ok
                  ? '窗口缩成贴在屏幕右侧、高 720 的窄条，只留启动/停止、模拟器画面、今天的结果和实时日志，不挡模拟器；点窄条右上角的 ⤢ 还原。'
                  : '切换成只有启动/停止、模拟器画面和实时日志的窄条布局。用新版桌面壳打开时，窗口还会缩小并贴到屏幕右侧。')),
              h('div', { class: 'sr-ctl' }, h('button', { type: 'button', class: 'btn', onclick: () => setCompact(true) }, icon('dock', 15), '切换到迷你模式'))),
            h('div', { class: 'set-row' },
              h('div', { class: 'sr-text' }, h('b', null, '快捷键'), h('small', null, '保存设置')),
              h('div', { class: 'sr-ctl' }, h('kbd', null, /Mac/.test(navigator.platform) ? '⌘ S' : 'Ctrl S')))),
          h('div', { class: 'set-group' },
            h('h2', null, icon('info', 16), '关于'),
            h('div', { class: 'about' }, logo(),
              h('div', { class: 'grow' }, h('b', null, 'ZJCSAutoScript'), h('small', null, '杖剑传说 · 每日自动化 · 配置保存在 '), h('code', null, file)))))));
  }

  function openErrors() {
    const groups = [...new Set(Object.keys(S.errors).map((k) => k.split('_')[0]))].filter(has);
    groups.forEach((g) => { if (!isSetting(g)) S.open.add(g); });
    saveOpen();
    if (groups.length) jumpTo(groups[0]);
    refresh();
  }

  async function save() {
    if (S.saving) return;
    if (!D.changes) {
      toast('没有要保存的改动');
      return;
    }
    if (Object.keys(S.errors).length) {
      openErrors();
      toast('有 ' + Object.keys(S.errors).length + ' 处要改一下才能保存', 'error');
      return;
    }
    S.saving = true;
    refresh();
    const r = await post('/api/config', { data: toData(S.cfg) });
    S.saving = false;
    if (r.status === 400 && r.data.errors) {
      S.errors = r.data.errors;
      openErrors();
      toast('有 ' + Object.keys(r.data.errors).length + ' 处要改一下才能保存', 'error');
    } else if (r.ok && r.data.data) {
      S.saved = toUi(r.data.data);
      S.cfg = toUi(r.data.data);
      S.errors = {};
      S.justSaved = true;
      toast(R.status && R.status.runtime.alive ? '已保存，脚本在下一项任务开始前用上新设置' : '已保存，下次运行时生效', 'ok');
    } else if (r.status) {
      toast('没保存上，再试一次', 'error');
    }
    refresh();
  }

  // 输入框有焦点时不会被刷新，撤销、恢复默认前先让它失焦
  const releaseFocus = () => { if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); };

  function undo() {
    releaseFocus();
    S.cfg = clone(S.saved);
    S.errors = {};
    refresh();
    toast('已撤销没保存的改动');
  }

  let toastTimer = 0;
  function toast(text, kind = '') {
    const el = document.getElementById('toast');
    el.replaceChildren(lvIcon(kind === 'error' ? 'err' : kind === 'ok' ? 'ok' : 'info'), h('span', null, text));
    el.className = 'toast show';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.className = 'toast'; }, kind === 'error' ? 4200 : 2400);
  }

  function refresh() {
    if (!S) return;
    derive();
    bindings.forEach((b) => b());
    tickSince();
  }

  // 「已经跑了 2:13」这类计时，每秒走一次，不用整页刷新
  function tickSince() {
    document.querySelectorAll('[data-since]').forEach((el) => {
      const since = el.getAttribute('data-since');
      const text = since ? clock(Date.now() - new Date(since).getTime()) : (el.getAttribute('data-empty') || '');
      if (el.textContent !== text) el.textContent = text;
    });
  }

  // ---------- 侧栏、顶栏 ----------
  function logo(cls = '') {
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('viewBox', '0 0 40 40');
    svg.setAttribute('class', 'logo' + (cls ? ' ' + cls : ''));
    svg.setAttribute('aria-hidden', 'true');
    svg.innerHTML = '<defs><linearGradient id="lgZ' + cls + '" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#3461ff"/><stop offset="1" stop-color="#5aa0ff"/></linearGradient></defs>'
      + '<rect width="40" height="40" rx="11" fill="url(#lgZ' + cls + ')"/><g fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round"><circle cx="12" cy="11.5" r="3"/><circle cx="28" cy="28.5" r="3"/><path d="M15.5 11.5h8a5 5 0 0 1 0 10h-7a5 5 0 0 0 0 10h8"/></g>';
    return svg;
  }

  function navMark(id) {
    if (id === 'run') return h('em', { class: () => 'nav-badge ' + runInfo().cls, show: () => !!runInfo().badge }, () => runInfo().badge);
    if (id === 'route' || id === 'settings') return h('i', { class: 'nav-dot', title: '有没保存的改动', show: () => D.pageChanges[id] > 0 });
    return null;
  }

  function sidebar() {
    const item = ([id, label, ic]) => h('a', {
      href: '#/' + id,
      class: () => 'nav-item' + (page === id ? ' on' : ''),
      'aria-current': () => (page === id ? 'page' : null),
      title: label,
    }, icon(ic, 18), h('span', null, label), navMark(id));
    const byId = (id) => PAGES.find((p) => p[0] === id);
    return h('aside', { class: 'sidebar' },
      h('div', { class: 'brand drag' }, logo(), h('div', { class: 'brand-text' }, h('b', null, 'ZJCSAutoScript'), h('span', null, '杖剑传说 · 每日自动化'))),
      h('nav', { class: 'nav', 'aria-label': '页面' },
        h('div', { class: 'nav-label' }, '脚本'),
        ['run', 'route', 'events', 'tools'].map((id) => item(byId(id))),
        h('div', { class: 'nav-label' }, '数据'),
        item(byId('logs'))),
      h('div', { class: 'nav-bottom' }, h('nav', { class: 'nav' }, item(byId('settings'))), connCard()));
  }

  function topbar() {
    const saveBtn = h('button', { type: 'button', class: 'btn btn-primary', 'aria-busy': () => String(S.saving), onclick: save },
      h('span', { class: 'spinner', 'aria-hidden': 'true', show: () => S.saving }),
      h('span', null, () => (S.saving ? '正在保存' : '保存')),
      h('kbd', { class: 'kbd' }, /Mac/.test(navigator.platform) ? '⌘S' : 'Ctrl S'));
    return h('header', { class: 'topbar drag' },
      h('div', { class: 'page-title' }, h('h1', null, () => pageInfo()[1]), h('span', null, () => pageInfo()[3])),
      h('div', { class: 'savebar' },
        h('span', { class: 'save-state dirty', show: () => D.changes > 0 }, h('i', { 'aria-hidden': 'true' }), () => '有 ' + D.changes + ' 处改动还没保存'),
        h('span', { class: 'save-state', show: () => D.changes === 0 && S.justSaved }, icon('check', 15), '已保存，下一项任务开始前生效'),
        h('button', { type: 'button', class: 'btn', show: () => D.changes > 0, onclick: undo }, '撤销'),
        h('span', { show: () => D.changes > 0, style: { display: 'contents' } }, saveBtn)),
      h('div', { class: 'top-icons' },
        h('button', { type: 'button', class: 'icon-btn', title: '迷你模式：缩成贴在屏幕右侧的小窗', 'aria-label': '迷你模式', onclick: () => setCompact(true) }, icon('dock', 18)),
        h('button', { type: 'button', class: 'icon-btn', title: () => (isDark() ? '换成浅色' : '换成深色'), 'aria-label': '切换深浅色', onclick: () => setTheme(isDark() ? 'light' : 'dark') },
          h('span', { show: () => !isDark(), style: { display: 'contents' } }, icon('moon', 18)),
          h('span', { show: () => isDark(), style: { display: 'contents' } }, icon('sun', 18)))),
      winctl());
  }

  // ---------- 迷你模式 ----------
  function miniView() {
    const running = () => !!runState().since;
    const step = () => {
      const s = runState();
      if (R.offline) return [null, '连不上配置服务'];
      if (s.kind === 'running') {
        const m = R.status ? queueModel() : null;
        const next = m && m.queue.concat(m.waiting)[0];
        return ['正在跑「' + nameOf(s.task) + '」', next ? '下一项：' + next.name : ''];
      }
      if (s.kind === 'waiting') return ['今天到期的都跑完了', s.next ? '下一次 ' + when(s.next) : ''];
      return [null, runInfo().meta];
    };
    const num = (key, label, cls) => h('div', { class: () => (todayCounts()[key] ? cls : 'zero') }, h('span', null, label), h('b', null, () => String(todayCounts()[key])));
    return h('div', { class: 'mini' },
      h('div', { class: 'mini-top drag' },
        logo('sm'), h('b', null, 'ZJCSAutoScript'), h('span', { class: 'grow' }),
        h('button', { type: 'button', class: 'icon-btn', title: '还原完整窗口', 'aria-label': '还原完整窗口', onclick: () => setCompact(false) }, icon('expand', 15)),
        h('button', { type: 'button', class: 'icon-btn close', title: '关闭', 'aria-label': '关闭', onclick: () => winAction('close') }, icon('x', 15))),
      h('div', { class: 'mini-panel' },
        h('div', { class: 'mini-head' },
          h('div', { class: 'status-row' },
            h('em', { class: () => 'status ' + runInfo().cls }, () => runInfo().pill),
            h('span', { class: () => 'timer' + (running() ? '' : ' dim'), 'data-since': () => runState().since || '', 'data-empty': '0:00' }, '0:00')),
          h('div', { class: 'mini-live' }, screenView(),
            h('div', { class: 'mini-nums' }, num('success', '今天完成', 'ok'), num('skip', '今天跳过', ''), num('failed', '今天失败', 'bad'))),
          h('div', { class: 'mini-step', title: () => step().filter(Boolean).join(' · ') },
            h('b', { show: () => !!step()[0] }, () => step()[0] || ''), h('span', { show: () => !!step()[0] && !!step()[1] }, ' · '), h('span', null, () => step()[1] || '')),
          runButton('mini', 'mini-run')),
        h('div', { class: 'mini-log-head' }, '实时日志', h('span', { class: 'grow' }),
          h('div', { class: 'mini-seg', role: 'group', 'aria-label': '显示哪些日志' },
            h('button', { type: 'button', 'aria-pressed': () => String(!MINI.onlyWarn), onclick: () => { MINI.onlyWarn = false; filterBox(miniBox, 'all', ''); refresh(); } }, '全部'),
            h('button', { type: 'button', 'aria-pressed': () => String(MINI.onlyWarn), onclick: () => { MINI.onlyWarn = true; filterBox(miniBox, 'warn', ''); refresh(); } }, '只看警告'))),
        miniBox),
      h('div', { class: 'mini-foot' }, h('span', { class: () => 'dot ' + deviceState()[0] }), h('span', { title: () => deviceState()[1] }, () => '模拟器' + deviceState()[1])));
  }

  // ---------- 启动 ----------
  function render() {
    const known = new Set(ROUTE.flatMap((r) => r[1]).concat(SETTINGS));
    const others = Object.keys(S.arg).filter((g) => !known.has(g));
    const otherTasks = others.filter((g) => !isSetting(g));
    const otherSettings = others.filter(isSetting);
    const groups = ROUTE.map(([title, tasks]) => [title, tasks]);
    if (otherTasks.length) groups.push(['其他', otherTasks]);
    const shown = groups.filter(([, tasks]) => tasks.some(has));
    const app = document.getElementById('app');
    derive();
    app.replaceChildren(
      h('div', { class: 'app' },
        sidebar(),
        h('div', { class: 'main' },
          topbar(),
          h('main', { class: 'panel' },
            runPage(),
            routePage(shown),
            emptyPage('events', '活动', 'flag', [
              '每个活动任务会写明开始和结束日期，过期后自动不跑，也不会混进每天的路线。',
              '有新活动要自动化时告诉我，打通后会出现在这一页。',
            ]),
            emptyPage('tools', '工具', 'tool', [
              '比如一次性的推图、批量领取这类不需要每天做的事。',
              '有需要时告诉我，做好后会出现在这一页，点一下就跑。',
            ]),
            logsPage(),
            settingsPage(SETTINGS.filter(has).concat(otherSettings))))),
      miniView());
    app.removeAttribute('aria-busy');
    refresh();
    showPage(page);
  }

  function fail(message) {
    const app = document.getElementById('app');
    app.replaceChildren(
      h('div', { class: 'topbar drag', style: { position: 'fixed', top: '0', left: '0', right: '0' } }, h('span', { class: 'grow' }), winctl()),
      h('div', { class: 'fail' },
        h('h1', null, '读不到配置'),
        h('p', null, message),
        h('button', { type: 'button', class: 'btn btn-primary', onclick: () => { app.replaceChildren(h('div', { class: 'boot' }, h('span', { class: 'spinner' }), '正在读取配置…')); boot(); } }, '再试一次')));
  }

  async function boot() {
    const desk = DESK.ok ? null : await initDesktop();
    try {
      const res = await fetch('/api/config', { cache: 'no-store' });
      if (!res.ok) throw new Error(String(res.status));
      const body = await res.json();
      const cfg = toUi(body.data);
      S = { arg: body.argument, mac: !!body.mac, file: body.file || '', cfg, saved: clone(cfg), defaults: defaultsOf(body.argument), open: loadOpen(), errors: {}, saving: false, justSaved: false };
      await pollStatus().catch(() => {});
      render();
      // 迷你模式下刷新了页面：窗口还是窄条，接着用迷你布局
      if (desk && desk.compact) setCompact(true);
      loadScreen();
      startTimers();
    } catch (e) {
      fail('配置服务没有响应。确认 gui.py 正在运行，然后再试一次。');
    }
  }

  // 定时器：运行状态每 2 秒（页面在后台时 10 秒），实时日志 1.5 秒，画面 3 秒（其他页面 30 秒，关了自动刷新就不截），计时每秒
  let timersStarted = false;
  function startTimers() {
    if (timersStarted) return;
    timersStarted = true;
    const last = { status: Date.now(), live: 0, screen: Date.now() };
    setInterval(() => {
      const now = Date.now();
      if (now - last.status >= (document.hidden ? 10000 : 2000)) { last.status = now; pollStatus(); }
      if (!document.hidden) {
        if (liveOn()) {
          if (now - last.live >= 1500) { last.live = now; pollLive(); }
          if (SC.auto && now - last.screen >= 3000) { last.screen = now; loadScreen(); }
        } else if (SC.auto && now - last.screen >= 30000) {
          last.screen = now;
          loadScreen();
        }
      }
      tickSince();
    }, 500);
  }

  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      if (S) save();
    } else if (e.key === 'Escape' && RM.open) {
      RM.open = '';
      refresh();
    }
  });
  window.addEventListener('beforeunload', (e) => {
    if (S && D.changes > 0) {
      e.preventDefault();
      e.returnValue = '';
    }
  });

  boot();
})();
