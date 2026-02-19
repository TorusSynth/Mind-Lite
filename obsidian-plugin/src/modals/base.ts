const DEFAULT_ERROR_TEXT = "Something went wrong. Please try again.";
const HIDDEN_CLASS = "mind-lite-modal__hidden";

type ActionHandler = (event: MouseEvent) => void | Promise<void>;

function configureAction(
  buttonEl: HTMLButtonElement,
  label: string,
  onClick: ActionHandler,
  isPrimary: boolean
): void {
  buttonEl.type = "button";
  buttonEl.textContent = label;
  buttonEl.classList.add("mind-lite-modal__action");

  if (isPrimary) {
    buttonEl.classList.add("mod-cta");
  } else {
    buttonEl.classList.remove("mod-cta");
  }

  buttonEl.onclick = (event) => {
    void onClick(event);
  };
}

export function showLoading(loadingEl: HTMLElement, isLoading: boolean, text = "Loading..."): void {
  loadingEl.textContent = text;
  loadingEl.classList.toggle(HIDDEN_CLASS, !isLoading);
}

export function showError(errorEl: HTMLElement, error: unknown | null | undefined): void {
  if (error == null) {
    errorEl.textContent = "";
    errorEl.classList.add(HIDDEN_CLASS);
    return;
  }

  const message = createErrorText(error);
  errorEl.textContent = message;
  errorEl.classList.remove(HIDDEN_CLASS);
}

export function setPrimaryAction(
  buttonEl: HTMLButtonElement,
  label: string,
  onClick: ActionHandler
): void {
  configureAction(buttonEl, label, onClick, true);
}

export function setSecondaryAction(
  buttonEl: HTMLButtonElement,
  label: string,
  onClick: ActionHandler
): void {
  configureAction(buttonEl, label, onClick, false);
}

export function createErrorText(error: unknown): string {
  if (typeof error === "string") {
    const value = error.trim();
    return value.length > 0 ? value : DEFAULT_ERROR_TEXT;
  }

  if (error instanceof Error) {
    const value = error.message.trim();
    return value.length > 0 ? value : DEFAULT_ERROR_TEXT;
  }

  if (typeof error === "object" && error !== null && "message" in error) {
    const value = String(error.message).trim();
    return value.length > 0 ? value : DEFAULT_ERROR_TEXT;
  }

  return DEFAULT_ERROR_TEXT;
}
