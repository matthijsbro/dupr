document.addEventListener('DOMContentLoaded', () => {
  const practiceItems = document.querySelectorAll('.practice-scroller-item');
  const practiceInput = document.querySelector('input[name="user_activity"]');

  function selectPractice(item) {
    practiceInput.value = item.dataset.practiceId;
    practiceItems.forEach(i => i.classList.toggle('selected', i === item));
    item.scrollIntoView({behavior: 'instant', inline: 'center', block: 'nearest'});
  }

  practiceItems.forEach(item => {
    item.addEventListener('click', () => selectPractice(item));
  });

  const initialItem = document.querySelector(`.practice-scroller-item[data-practice-id="${practiceInput.value}"]`);
  if (initialItem) {
    selectPractice(initialItem);
  }

  const tabs = document.querySelectorAll('#inputTypeTabsContainer [role="tab"]');
  const sections = {
    malas: document.getElementById('malasInputSection'),
    time: document.getElementById('timeInputSection'),
  };
  function show(type) {
    tabs.forEach(t => t.classList.toggle('tab-active', t.dataset.type === type));
    sections.malas.classList.toggle('hidden', type !== 'malas');
    sections.time.classList.toggle('hidden', type !== 'time');
  }
  tabs.forEach(t => t.addEventListener('click', () => show(t.dataset.type)));
  show('malas');

  const malasInput = document.getElementById('id_malas_submitted');
  const malasDisplay = document.getElementById('malasCountDisplay');
  document.getElementById('malasIncrementBtn').addEventListener('click', () => {
    malasInput.value = (parseInt(malasInput.value || 0) + 1);
    malasDisplay.textContent = malasInput.value;
  });
  document.getElementById('malasDecrementBtn').addEventListener('click', () => {
    malasInput.value = Math.max(0, parseInt(malasInput.value || 0) - 1);
    malasDisplay.textContent = malasInput.value;
  });
  malasDisplay.textContent = malasInput.value || '0';

  const hoursInput = document.getElementById('id_time_submitted_hours');
  const minutesInput = document.getElementById('id_time_submitted_minutes');
  const timeSlider = document.getElementById('timeSlider');
  const timeDisplay = document.getElementById('timeDisplay');
  const hrLabel = timeDisplay.dataset.hrLabel || 'hr';
  const minLabel = timeDisplay.dataset.minLabel || 'min';
  function updateTime(total) {
    const h = Math.floor(total / 60);
    const m = total % 60;
    hoursInput.value = h;
    minutesInput.value = m;
    timeDisplay.textContent = `${h} ${hrLabel} ${m} ${minLabel}`;
  }
  timeSlider.addEventListener('input', e => updateTime(parseInt(e.target.value)));
  const startTotal = (parseInt(hoursInput.value) || 0) * 60 + (parseInt(minutesInput.value) || 0);
  timeSlider.value = startTotal;
  updateTime(startTotal);

  const dateInput = document.querySelector('input.log-date-input');
  const dateDisplay = document.getElementById('formattedDateDisplay');
  const selectLabel = dateDisplay.dataset.selectLabel || 'Select Date';
  function updateDate() {
    if (!dateInput.value) {
      dateDisplay.textContent = selectLabel;
      return;
    }
    const d = new Date(dateInput.value);
    dateDisplay.textContent = d.toLocaleDateString(undefined, { day: '2-digit', month: 'long', year: 'numeric' });
  }
  dateInput.addEventListener('input', updateDate);
  dateDisplay.addEventListener('click', () => { if (dateInput.showPicker) dateInput.showPicker(); });
  updateDate();
});
