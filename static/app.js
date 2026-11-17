document.querySelectorAll('[data-confirm]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

document.querySelectorAll('[data-kind-select]').forEach((kind) => {
  const category = kind.form.querySelector('[data-category-select]');
  const update = () => {
    const income = kind.value === 'income';
    for (const option of category.options) {
      option.hidden = income ? option.value !== 'Income' : option.value === 'Income';
    }
    if (income && category.value !== 'Income') category.value = 'Income';
    if (!income && category.value === 'Income') category.value = 'Food';
  };
  kind.addEventListener('change', update);
  update();
});
