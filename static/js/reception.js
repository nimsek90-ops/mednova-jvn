document.querySelectorAll('[data-select-search]').forEach(input => {
  const select = document.getElementById(input.dataset.selectSearch);
  if (!select) return;
  input.addEventListener('input', () => {
    const query = input.value.trim().toLocaleLowerCase();
    Array.from(select.options).forEach(option => {
      option.hidden = Boolean(option.value && !option.selected && !option.textContent.toLocaleLowerCase().includes(query));
    });
  });
});
