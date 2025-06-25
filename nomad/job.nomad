job "sandboxed-agent" {
  datacenters = ["dc1"]
  type        = "service"

  group "agent-group" {
    count = 2

    network {
      port "api"   { to = 8000 }
      port "novnc" { to = 6080 }
    }

    task "agent" {
      driver = "docker"

      config {
        image = "sandboxed-agent:latest"
        privileged = true # Firecracker & nested virtualization
      }

      resources {
        cpu    = 1000  # MHz
        memory = 1024  # MB
      }

      service {
        name = "sandboxed-agent"
        port = "api"
        tags = ["api"]
      }
    }
  }
} 