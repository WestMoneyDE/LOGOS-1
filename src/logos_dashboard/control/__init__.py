"""Control plane: pure state machines, DAG, queue and the service layer that persists transitions as events + audit rows.
No model call, except the opt-in Laya shadow (LOGOS_LAYA_SHADOW=1): after a transition commits, service.advance asks the
local Laya service for its move and records it as one `laya.shadow` audit row; it cannot change the thesis."""
