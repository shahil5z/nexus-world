"""TensorFlow deep ensemble for the residual of the linear transition model (offline training only)."""
from __future__ import annotations

import numpy as np


def train_ensemble(X, r, n_members=5, seed=42, hidden=(16, 16), max_epochs=500, patience=30):
    import tensorflow as tf  # imported lazily: never needed at runtime

    mean, scale = X.mean(axis=0), X.std(axis=0)
    scale[scale == 0] = 1.0
    Z = (X - mean) / scale
    n_val = max(24, int(0.15 * len(Z)))           # chronological inner validation (last 15% of train)
    Ztr, rtr, Zva, rva = Z[:-n_val], r[:-n_val], Z[-n_val:], r[-n_val:]
    members, histories = [], []
    for i in range(n_members):
        tf.keras.utils.set_random_seed(seed + i)
        try:
            tf.config.experimental.enable_op_determinism()
        except Exception:  # noqa: BLE001 - older TF builds
            pass
        model = tf.keras.Sequential([tf.keras.Input(shape=(Z.shape[1],))] + [
            tf.keras.layers.Dense(h, activation="relu", kernel_regularizer=tf.keras.regularizers.l2(1e-3)) for h in hidden
        ] + [tf.keras.layers.Dense(1)])
        model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="huber", metrics=["mae"])
        es = tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=patience, restore_best_weights=True)
        h = model.fit(Ztr, rtr, validation_data=(Zva, rva), epochs=max_epochs, batch_size=32, shuffle=True,
                      callbacks=[es], verbose=0)
        layers = tuple((l.get_weights()[0].astype(np.float64), l.get_weights()[1].astype(np.float64))
                       for l in model.layers if l.get_weights())
        members.append(layers)
        histories.append({"epochs_run": len(h.history["loss"]),
                          "best_val_loss": float(np.min(h.history["val_loss"])),
                          "final_train_loss": float(h.history["loss"][-1])})
        tf_pred = model.predict(Z, verbose=0)[:, 0]
        if i == 0:
            first_tf_pred = tf_pred
    return mean, scale, members, histories, first_tf_pred
