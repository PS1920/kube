import time

class DeploymentStateEngine:
    def __init__(self, tolerance_seconds=30):
        self.tolerance_seconds = tolerance_seconds
        self.deployments = {} # deployment_name -> tracking dict

    def _derive_event_message(self, prev, curr):
        if prev == curr:
            return ""
            
        if curr == "healthy":
            if prev == "recovering":
                return "System recovered successfully"
            return "System stabilized"
            
        if curr == "recovering":
            return "Self-healing in progress"
            
        if curr == "degraded":
            return "Degradation detected"
            
        if curr == "failure":
            if prev == "degraded":
                return "Escalation: Service failure detected"
            return "Failure detected"
            
        return ""

    def evaluate_deployments(self, raw_deploys):
        """Called every tick or event to ingest raw counts."""
        seen = set()
        
        for d in raw_deploys:
            name = d.metadata.name
            seen.add(name)
            
            # Explicitly typecast K8s client response defaults
            ready = d.status.ready_replicas
            running = 0 if ready is None else ready
            
            spec_rep = d.spec.replicas
            desired = 1 if spec_rep is None else spec_rep
            
            if name not in self.deployments:
                self.deployments[name] = {
                    "state": "healthy",
                    "previous_state": "healthy",
                    "disruption_start_time": None,
                    "running": running,
                    "desired": desired,
                    "event_message": "System stabilized",
                    "namespace": d.metadata.namespace
                }
            
            self.deployments[name]["running"] = running
            self.deployments[name]["desired"] = desired
            self.deployments[name]["namespace"] = d.metadata.namespace
            
        # Clean up deleted natively
        for k in list(self.deployments.keys()):
            if k not in seen:
                del self.deployments[k]

    def tick(self):
        """Computes the internal state machine evaluating durations against tolerance."""
        now = time.time()
        changes = []
        
        for name, data in self.deployments.items():
            running = data["running"]
            desired = data["desired"]
            curr_state = data["state"]
            
            new_state = curr_state
            
            if running >= desired:
                new_state = "healthy"
                data["disruption_start_time"] = None
            else:
                if data["disruption_start_time"] is None:
                    data["disruption_start_time"] = now
                
                duration = now - data["disruption_start_time"]
                
                if duration < self.tolerance_seconds:
                    new_state = "recovering"
                else:
                    if running > 0:
                        new_state = "degraded"
                    else:
                        new_state = "failure"
                        
            if new_state != curr_state:
                data["previous_state"] = curr_state
                data["state"] = new_state
                msg = self._derive_event_message(curr_state, new_state)
                data["event_message"] = msg
                changes.append({
                    "service": name,
                    "status": new_state
                })
                
            # DEBUG LOGGING (Ensure consistency is verifiable)
            print(f"[STATE_ENGINE] {name} | Desired: {desired} | Ready: {running} | Status: {new_state}")
                
        return changes
        
    def get_snapshot(self):
        """Format payload natively for Websockets & API delivery."""
        arr = []
        for name, data in self.deployments.items():
            arr.append({
                "name": name,
                "status": data["state"],
                "running": data["running"],
                "desired": data["desired"],
                "event_message": data["event_message"],
                "namespace": data["namespace"]
            })
        return arr

state_engine = DeploymentStateEngine(tolerance_seconds=30)
