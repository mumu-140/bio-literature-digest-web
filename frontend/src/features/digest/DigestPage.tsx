import { AuthUser } from "../../dataClient";
import { DigestControls } from "./DigestControls";
import { DigestGroups } from "./DigestGroups";
import { ToastState, useDigestLibrary } from "./useDigestLibrary";

export function DigestPage({ user }: { user: AuthUser }) {
  const digest = useDigestLibrary({ user });

  return (
    <div className="content-stack">
      {digest.favoriteToast ? (
        <ToastBanner toast={digest.favoriteToast} onClose={() => digest.setFavoriteToast(null)} />
      ) : null}
      <section className="card">
        <DigestControls user={user} digest={digest} />
        <DigestGroups user={user} digest={digest} />
      </section>
    </div>
  );
}

function ToastBanner({ toast, onClose }: { toast: ToastState; onClose: () => void }) {
  return (
    <div className={"top-toast is-" + toast.kind} role="status" aria-live="polite">
      <span>{toast.message}</span>
      <button className="top-toast-close" onClick={onClose} aria-label="关闭提示">×</button>
    </div>
  );
}
