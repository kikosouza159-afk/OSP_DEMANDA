// Painel de Demandas + Checkpoint Locator
(function () {
  'use strict';

  const CHECKPOINT_FIELDS = [
    { key: 'tipo_agente_virtual', label: 'Tipo de Agente Virtual', type: 'select', obs: 'Lista fixa: Locator / Sem informação no Painel' },
    { key: 'organizacao', label: 'Organização', type: 'text', obs: 'Campo variável' },
    { key: 'plano_tabulacao', label: 'Plano de Tabulação', type: 'text', obs: 'Campo variável' },
    { key: 'horario', label: 'Horário', type: 'time-range', start: 'horario_inicio', end: 'horario_fim', obs: 'Campo com relógio para configurar início e fim' },
    { key: 'recursos_midia', label: 'Recursos de Mídia', type: 'text', obs: 'Campo variável' },
    { key: 'lcr_rota', label: 'LCR ROTA', type: 'text', obs: 'Campo variável' },
    { key: 'rota_portal_voz', label: 'Rota para Portal de Voz', type: 'select', obs: 'Lista selecionável' },
    { key: 'canais', label: 'Canais', type: 'number', obs: 'Campo variável numérico' },
    { key: 'url_aplicacao', label: 'Url da Aplicação', type: 'url', obs: 'Campo variável com URL da aplicação' },
    { key: 'dnis_portal_voz', label: 'DNIS para o Portal de Voz', type: 'text', obs: 'Campo variável' },
    { key: 'tempo_maximo_chamada', label: 'Tempo máximo chamada', type: 'number', obs: 'Campo variável em segundos' },
    { key: 'campanha_receptiva', label: 'Campanha Receptiva', type: 'text', obs: 'Campo variável' },
    { key: 'calculo_demanda', label: 'Cálculo de demanda', type: 'select', obs: 'Lista: Balanceado / Apenas Ativo / Pelo Receptivo' },
    { key: 'portal_voz', label: 'Portal de Voz', type: 'select', obs: 'Lista selecionável' },
    { key: 'plano_tarifacao_telecom', label: 'Plano de Tarifação Telecom', type: 'text', obs: 'Campo variável' },
    { key: 'plano_tarifacao_agentes_digitais', label: 'Planos de tarifação dos agentes digitais', type: 'text', obs: 'Campo variável' },
    { key: 'gestor_negocio', label: 'Cadastrar no Gestor de Negócio', type: 'select', obs: 'Lista: Cadastrado / Pendente' },
  ];

  const SELECT_OPTIONS = {
    tipo_agente_virtual: ['Locator', 'Sem informação no Painel'],
    rota_portal_voz: ['SIPADA', 'Sem informação'],
    calculo_demanda: ['Balanceado', 'Apenas Ativo', 'Pelo Receptivo'],
    portal_voz: ['KAMAILIO_Locator', 'Sem informação'],
    gestor_negocio: ['Cadastrado', 'Pendente'],
  };

  function qs(id) { return document.getElementById(id); }

  function initPainelDemandas() {
    let mouseFrame = null;
    window.addEventListener('pointermove', (event) => {
      if (mouseFrame) return;
      mouseFrame = requestAnimationFrame(() => {
        document.body.style.setProperty('--mx', `${(event.clientX / window.innerWidth) * 100}%`);
        document.body.style.setProperty('--my', `${(event.clientY / window.innerHeight) * 100}%`);
        mouseFrame = null;
      });
    });

    const tableBody = qs('demandTableBody');
    const searchInput = qs('searchInput');
    const statusFilter = qs('statusFilter');
    const analistaFilter = qs('analistaFilter');
    const refreshBtn = qs('refreshBtn');
    const newDemandBtn = qs('newDemandBtn');
    const modal = qs('demandModal');
    const form = qs('demandForm');
    const toast = qs('toast');
    const closeModalBtn = qs('closeModalBtn');
    const cancelBtn = qs('cancelBtn');
    const checkpointSelect = qs('checkpointDemandaSelect');
    const checkpointTableBody = qs('checkpointTableBody');
    const saveCheckpointBtn = qs('saveCheckpointBtn');
    const resetCheckpointBtn = qs('resetCheckpointBtn');
    const refreshIndicatorsBtn = qs('refreshIndicatorsBtn');

    let demandas = [];
    let currentCheckpoint = null;
    let currentCheckpointDemand = null;
    let debounceTimer = null;

    function statusSlug(status) {
      return String(status || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    }

    function showToast(message) {
      toast.textContent = message;
      toast.classList.add('show');
      window.setTimeout(() => toast.classList.remove('show'), 2600);
    }

    function brDate(value, fallback = 'Sem previsão') {
      if (!value) return fallback;
      const [y, m, d] = value.split('-');
      return y && m && d ? `${d}/${m}/${y}` : value;
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>'"]/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;'
      }[char]));
    }

    function updateCards(cards = {}) {
      qs('cardTotal').textContent = cards.Total ?? 0;
      qs('cardImplantado').textContent = cards.Implantado ?? 0;
      qs('cardPOC').textContent = cards.POC ?? 0;
      qs('cardHomolog').textContent = cards['Homolog cliente'] ?? 0;
      qs('cardFila').textContent = cards['Fila OSP'] ?? 0;
      qs('cardMapeamento').textContent = cards['Em Mapeamento'] ?? 0;
    }

    function renderDemandOptions() {
      const selected = checkpointSelect.value;
      checkpointSelect.innerHTML = '<option value="">Selecione uma demanda</option>' + demandas.map(item => {
        const label = `#${item.id} - ${item.cliente}${item.carteira ? ' | ' + item.carteira : ''}`;
        return `<option value="${item.id}">${escapeHtml(label)}</option>`;
      }).join('');
      if (selected) checkpointSelect.value = selected;
    }

    function renderTable(items) {
      demandas = items || [];
      renderDemandOptions();
      if (!demandas.length) {
        tableBody.innerHTML = '<tr><td colspan="11" class="empty-state">Nenhuma demanda encontrada para os filtros selecionados.</td></tr>';
        return;
      }

      tableBody.innerHTML = demandas.map(item => {
        const statusClass = `status-${statusSlug(item.status_etapa_atual)}`;
        const wrike = item.wrike ? `<a class="wrike-link" href="${escapeHtml(item.wrike)}" target="_blank" rel="noopener">Abrir</a>` : '';
        return `
          <tr>
            <td>${escapeHtml(item.acompanhamento)}</td>
            <td class="center"><strong>${item.id}</strong></td>
            <td>${escapeHtml(item.cliente)}</td>
            <td>${escapeHtml(item.validacao_dados_locator)}</td>
            <td>${escapeHtml(item.carteira)}</td>
            <td><span class="status-pill ${statusClass}">${escapeHtml(item.status_etapa_atual)}</span></td>
            <td class="center">${item.dias_poc ?? ''}</td>
            <td>${item.inicio_poc ? brDate(item.inicio_poc) : 'Sem previsão'}</td>
            <td>${item.final_poc ? brDate(item.final_poc) : 'Sem previsão'}</td>
            <td>${wrike}</td>
            <td>
              <div class="row-actions">
                <button type="button" class="action-btn check" data-action="checkpoint" data-id="${item.id}" title="Checkpoint">✓</button>
                <button type="button" class="action-btn" data-action="edit" data-id="${item.id}" title="Editar">✎</button>
                <button type="button" class="action-btn danger" data-action="delete" data-id="${item.id}" title="Excluir">×</button>
              </div>
            </td>
          </tr>`;
      }).join('');
    }

    async function loadDemandas() {
      const params = new URLSearchParams();
      if (searchInput.value.trim()) params.set('search', searchInput.value.trim());
      if (statusFilter.value) params.set('status', statusFilter.value);
      if (analistaFilter.value) params.set('analista', analistaFilter.value);
      const response = await fetch(`/api/demandas?${params.toString()}`);
      if (!response.ok) throw new Error('Erro ao carregar demandas');
      const data = await response.json();
      updateCards(data.cards || {});
      renderTable(data.items || []);
    }

    function setView(name) {
      document.querySelectorAll('.view-section').forEach(view => view.classList.remove('active'));
      document.querySelectorAll('.nav-icon[data-view]').forEach(btn => btn.classList.remove('active'));
      const view = qs(`${name}View`);
      if (view) view.classList.add('active');
      const btn = document.querySelector(`.nav-icon[data-view="${name}"]`);
      if (btn) btn.classList.add('active');
      if (name === 'indicadores') loadIndicadores().catch(handleLoadError);
    }

    function resetForm() {
      form.reset();
      qs('demandaId').value = '';
      qs('idDisplay').value = 'Automático';
      qs('status_etapa_atual').value = 'Em Mapeamento';
    }

    function openModal() {
      modal.hidden = false;
      modal.removeAttribute('hidden');
      modal.classList.add('open');
      document.body.classList.add('modal-open');
      window.setTimeout(() => qs('cliente').focus(), 80);
    }

    function closeModal() {
      modal.classList.remove('open');
      document.body.classList.remove('modal-open');
      window.setTimeout(() => { modal.hidden = true; }, 120);
    }

    function openCreate() {
      resetForm();
      qs('modalTitle').textContent = 'Nova Demanda';
      openModal();
    }

    function openEdit(id) {
      const item = demandas.find(d => Number(d.id) === Number(id));
      if (!item) return;
      qs('modalTitle').textContent = `Editar Demanda #${id}`;
      qs('demandaId').value = item.id;
      qs('idDisplay').value = item.id;
      qs('acompanhamento').value = item.acompanhamento || '';
      qs('cliente').value = item.cliente || '';
      qs('validacao_dados_locator').value = item.validacao_dados_locator || '';
      qs('carteira').value = item.carteira || '';
      qs('status_etapa_atual').value = item.status_etapa_atual || 'Em Mapeamento';
      qs('inicio_poc').value = item.inicio_poc || '';
      qs('final_poc').value = item.final_poc || '';
      qs('wrike').value = item.wrike || '';
      openModal();
    }

    async function deleteDemand(id) {
      const item = demandas.find(d => Number(d.id) === Number(id));
      const label = item ? `${item.cliente} | ${item.carteira || 'sem carteira'}` : `ID ${id}`;
      if (!confirm(`Excluir a demanda ${label}? O checkpoint vinculado também será removido.`)) return;
      const response = await fetch(`/api/demandas/${id}`, { method: 'DELETE' });
      if (!response.ok) return showToast('Não foi possível excluir.');
      showToast('Demanda excluída.');
      if (checkpointSelect.value === String(id)) clearCheckpointView();
      await loadDemandas();
    }

    function getPayload() {
      return {
        acompanhamento: qs('acompanhamento').value,
        cliente: qs('cliente').value,
        validacao_dados_locator: qs('validacao_dados_locator').value,
        carteira: qs('carteira').value,
        status_etapa_atual: qs('status_etapa_atual').value,
        inicio_poc: qs('inicio_poc').value,
        final_poc: qs('final_poc').value,
        wrike: qs('wrike').value,
      };
    }

    function isConfigured(checkpoint, field) {
      if (field.type === 'time-range') {
        return Boolean((checkpoint[field.start] || '').trim() && (checkpoint[field.end] || '').trim());
      }
      return Boolean((checkpoint[field.key] || '').trim());
    }

    function fieldValue(checkpoint, field) {
      if (field.type === 'time-range') {
        return `${checkpoint[field.start] || ''} às ${checkpoint[field.end] || ''}`.replace(/^ às $/, '');
      }
      return checkpoint[field.key] || '';
    }

    function renderInput(field, checkpoint) {
      if (field.type === 'time-range') {
        return `<div class="time-range"><input type="time" data-check-field="${field.start}" value="${escapeHtml(checkpoint[field.start] || '')}"><span>às</span><input type="time" data-check-field="${field.end}" value="${escapeHtml(checkpoint[field.end] || '')}"></div>`;
      }
      if (field.type === 'select') {
        const value = checkpoint[field.key] || '';
        const options = (SELECT_OPTIONS[field.key] || []).map(opt => `<option value="${escapeHtml(opt)}" ${opt === value ? 'selected' : ''}>${escapeHtml(opt)}</option>`).join('');
        return `<select data-check-field="${field.key}"><option value="">Selecione</option>${options}</select>`;
      }
      const inputType = field.type === 'number' ? 'number' : field.type === 'url' ? 'url' : 'text';
      return `<input type="${inputType}" data-check-field="${field.key}" value="${escapeHtml(fieldValue(checkpoint, field))}" placeholder="Informe o valor">`;
    }

    function updateCheckpointCards(checkpoint = {}) {
      qs('checkpointTotal').textContent = checkpoint.total_count ?? 0;
      qs('checkpointOk').textContent = checkpoint.filled_count ?? 0;
      qs('checkpointPending').textContent = checkpoint.pending_count ?? 0;
      qs('checkpointPercent').textContent = `${checkpoint.completion_percent ?? 0}%`;
    }

    function clearCheckpointView() {
      currentCheckpoint = null;
      currentCheckpointDemand = null;
      checkpointSelect.value = '';
      qs('checkpointDemandTitle').textContent = 'Nenhuma demanda selecionada';
      qs('checkpointDemandSubtitle').textContent = 'Escolha uma demanda para abrir o checklist.';
      checkpointTableBody.innerHTML = '<tr><td colspan="4" class="empty-state">Selecione uma demanda para carregar o checklist.</td></tr>';
      qs('checkpointObservacoes').value = '';
      updateCheckpointCards({ total_count: 0, filled_count: 0, pending_count: 0, completion_percent: 0 });
    }

    function renderCheckpoint(demanda, checkpoint) {
      currentCheckpoint = checkpoint;
      currentCheckpointDemand = demanda;
      checkpointSelect.value = demanda.id;
      qs('checkpointDemandTitle').textContent = `#${demanda.id} - ${demanda.cliente}`;
      qs('checkpointDemandSubtitle').textContent = `${demanda.carteira || 'Sem carteira'} • ${demanda.validacao_dados_locator || 'Validação não informada'}`;
      updateCheckpointCards(checkpoint);
      qs('checkpointObservacoes').value = checkpoint.observacoes || '';

      checkpointTableBody.innerHTML = CHECKPOINT_FIELDS.map(field => {
        const ok = isConfigured(checkpoint, field);
        return `<tr class="${ok ? 'check-ok' : 'check-pending'}">
          <td><strong>${escapeHtml(field.label)}</strong></td>
          <td>${renderInput(field, checkpoint)}</td>
          <td>${ok ? '<span class="check-status ok">✓ Configurado</span>' : '<span class="check-status pending">! Pendente</span>'}</td>
          <td class="muted-text">${escapeHtml(field.obs)}</td>
        </tr>`;
      }).join('');
    }

    async function loadCheckpoint(demandaId) {
      if (!demandaId) return clearCheckpointView();
      const response = await fetch(`/api/demandas/${demandaId}/checkpoint`);
      if (!response.ok) throw new Error('Erro ao carregar checkpoint');
      const data = await response.json();
      renderCheckpoint(data.demanda, data.checkpoint);
      setView('checkpoint');
    }

    function getCheckpointPayload() {
      const payload = {};
      checkpointTableBody.querySelectorAll('[data-check-field]').forEach(input => {
        payload[input.dataset.checkField] = input.value;
      });
      payload.observacoes = qs('checkpointObservacoes').value;
      return payload;
    }

    async function saveCheckpoint() {
      const demandaId = currentCheckpointDemand?.id || checkpointSelect.value;
      if (!demandaId) return showToast('Selecione uma demanda primeiro.');
      const response = await fetch(`/api/demandas/${demandaId}/checkpoint`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(getCheckpointPayload()),
      });
      if (!response.ok) return showToast('Não foi possível salvar o checkpoint.');
      const data = await response.json();
      renderCheckpoint(data.demanda, data.checkpoint);
      showToast('Checkpoint salvo.');
    }

    async function resetCheckpoint() {
      const demandaId = currentCheckpointDemand?.id || checkpointSelect.value;
      if (!demandaId) return showToast('Selecione uma demanda primeiro.');
      if (!confirm('Aplicar o modelo padrão e sobrescrever os campos deste checkpoint?')) return;
      const response = await fetch(`/api/demandas/${demandaId}/checkpoint/reset`, { method: 'POST' });
      if (!response.ok) return showToast('Não foi possível aplicar o modelo padrão.');
      const data = await response.json();
      renderCheckpoint(data.demanda, data.checkpoint);
      showToast('Modelo padrão aplicado.');
    }


    function farolIcon(farol) {
      const map = { Verde: '🟢', Amarelo: '🟡', Laranja: '🟠', Vermelho: '🔴' };
      return map[farol] || '⚪';
    }

    function updateIndicatorsCards(cards = {}) {
      qs('indTotalDemandas').textContent = cards.total_demandas ?? 0;
      qs('indImplantacao').textContent = cards.em_implantacao_poc ?? 0;
      qs('indImplantadas').textContent = cards.implantadas ?? 0;
      qs('indPendConfig').textContent = cards.pendentes_configuracao ?? 0;
      qs('indMediaCheckpoint').textContent = `${cards.conclusao_media_checkpoint ?? 0}%`;
      qs('indVencidas').textContent = cards.demandas_vencidas ?? 0;
    }

    function renderStatusChart(statusCounts = {}) {
      const container = qs('statusChart');
      const entries = Object.entries(statusCounts);
      const max = Math.max(...entries.map(([, value]) => Number(value) || 0), 1);
      container.innerHTML = entries.map(([label, value]) => {
        const pct = Math.round(((Number(value) || 0) / max) * 100);
        return `<div class="bar-row">
          <div class="bar-label"><span>${escapeHtml(label)}</span><strong>${value}</strong></div>
          <div class="bar-track"><div class="bar-fill status-${statusSlug(label)}" style="width:${pct}%"></div></div>
        </div>`;
      }).join('') || '<p class="empty-state">Sem dados de status.</p>';
    }

    function renderPrazoGrid(prazoCounts = {}) {
      const labels = ['No prazo', 'Vence em até 3 dias', 'Vencidas', 'Sem previsão'];
      qs('prazoGrid').innerHTML = labels.map(label => `<div class="mini-card prazo-${statusSlug(label)}">
        <span>${escapeHtml(label)}</span>
        <strong>${prazoCounts[label] ?? 0}</strong>
      </div>`).join('');
    }

    function renderAnalistas(rows = []) {
      const body = qs('analistaIndicatorBody');
      if (!rows.length) {
        body.innerHTML = '<tr><td colspan="5" class="empty-state">Sem dados por analista.</td></tr>';
        return;
      }
      body.innerHTML = rows.map(row => `<tr>
        <td><strong>${escapeHtml(row.analista)}</strong></td>
        <td class="center">${row.total}</td>
        <td class="center">${row.poc}</td>
        <td class="center">${row.fila_osp}</td>
        <td class="center"><span class="pending-chip">${row.pendentes_checkpoint}</span></td>
      </tr>`).join('');
    }

    function renderPendingRanking(rows = []) {
      const container = qs('pendingRanking');
      const max = Math.max(...rows.map(row => Number(row.qtde) || 0), 1);
      if (!rows.length) {
        container.innerHTML = '<p class="empty-state">Nenhuma pendência encontrada. Céu limpo no radar.</p>';
        return;
      }
      container.innerHTML = rows.map(row => {
        const pct = Math.round(((Number(row.qtde) || 0) / max) * 100);
        return `<div class="ranking-row">
          <div><strong>${escapeHtml(row.campo)}</strong><span>${row.qtde} pendência(s)</span></div>
          <div class="bar-track"><div class="bar-fill warning" style="width:${pct}%"></div></div>
        </div>`;
      }).join('');
    }

    function renderFarol(rows = []) {
      const body = qs('farolTableBody');
      if (!rows.length) {
        body.innerHTML = '<tr><td colspan="8" class="empty-state">Sem dados no farol.</td></tr>';
        return;
      }
      body.innerHTML = rows.map(row => `<tr>
        <td class="center"><strong>${row.id}</strong></td>
        <td>${escapeHtml(row.cliente)}</td>
        <td>${escapeHtml(row.carteira)}</td>
        <td><span class="status-pill status-${statusSlug(row.status)}">${escapeHtml(row.status)}</span></td>
        <td class="center"><span class="percent-chip">${row.checkpoint_percent}%</span></td>
        <td class="center">${row.pendentes}</td>
        <td>${escapeHtml(row.final_poc)}</td>
        <td class="center"><span class="farol-chip farol-${statusSlug(row.farol)}">${farolIcon(row.farol)} ${escapeHtml(row.farol)}</span></td>
      </tr>`).join('');
    }

    async function loadIndicadores() {
      const response = await fetch('/api/indicadores');
      if (!response.ok) throw new Error('Erro ao carregar indicadores');
      const data = await response.json();
      updateIndicatorsCards(data.cards || {});
      renderStatusChart(data.status_counts || {});
      renderPrazoGrid(data.prazo_counts || {});
      renderAnalistas(data.analistas || []);
      renderPendingRanking(data.ranking_pendencias || []);
      renderFarol(data.farol_clientes || []);
    }

    document.querySelectorAll('.nav-icon[data-view]').forEach(btn => {
      btn.addEventListener('click', () => setView(btn.dataset.view));
    });

    newDemandBtn.addEventListener('click', (event) => { event.preventDefault(); openCreate(); });
    refreshBtn.addEventListener('click', loadDemandas);
    closeModalBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    saveCheckpointBtn.addEventListener('click', saveCheckpoint);
    resetCheckpointBtn.addEventListener('click', resetCheckpoint);
    refreshIndicatorsBtn?.addEventListener('click', () => loadIndicadores().catch(handleLoadError));
    checkpointSelect.addEventListener('change', () => loadCheckpoint(checkpointSelect.value).catch(handleLoadError));

    modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(); });
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && modal.classList.contains('open')) closeModal(); });

    tableBody.addEventListener('click', (event) => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;
      const id = button.dataset.id;
      if (button.dataset.action === 'edit') openEdit(id);
      if (button.dataset.action === 'delete') deleteDemand(id);
      if (button.dataset.action === 'checkpoint') loadCheckpoint(id).catch(handleLoadError);
    });

    [searchInput, statusFilter, analistaFilter].forEach(el => {
      el.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = window.setTimeout(() => loadDemandas().catch(handleLoadError), 240);
      });
      el.addEventListener('change', () => loadDemandas().catch(handleLoadError));
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const id = qs('demandaId').value;
      const response = await fetch(id ? `/api/demandas/${id}` : '/api/demandas', {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(getPayload()),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        return showToast(error.error || 'Não foi possível salvar.');
      }
      closeModal();
      showToast(id ? 'Demanda atualizada.' : 'Demanda criada.');
      await loadDemandas();
    });

    function handleLoadError(error) {
      console.error(error);
      showToast('Erro ao carregar painel.');
    }

    window.painelDemandasDebug = {
      abrirNovaDemanda: openCreate,
      abrirCheckpoint: loadCheckpoint,
      salvarCheckpoint: saveCheckpoint,
      recarregar: loadDemandas,
      carregarIndicadores: loadIndicadores,
    };

    loadDemandas().catch(handleLoadError);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPainelDemandas);
  } else {
    initPainelDemandas();
  }
})();
