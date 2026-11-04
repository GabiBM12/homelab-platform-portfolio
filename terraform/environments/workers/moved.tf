# Preserve existing VM state addresses when adopting K3s names.
moved {
  from = module.vm["k8s-worker-01"]
  to   = module.vm["k3s-worker-01"]
}

moved {
  from = module.vm["k8s-worker-02"]
  to   = module.vm["k3s-worker-02"]
}
