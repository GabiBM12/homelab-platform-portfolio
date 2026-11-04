# Preserve existing VM state addresses when adopting K3s names.
moved {
  from = module.vm["k8s-cp-01"]
  to   = module.vm["k3s-cp-01"]
}
