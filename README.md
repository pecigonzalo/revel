# Revel

Personal remove development environments.

## Status

This project is in active development to reach v1.

- [x] Create
- [x] Destroy
- [x] List
- [x] Refresh
- [ ] Provision
- [ ] Sync
- [ ] Stop
- [ ] Start
- [ ] Releases automation
- [ ] Integration tests
- [ ] GCP Support

## Description

This project aims to provide a relatively simple CLI to provision remove development envioronments.

Now that we have amazing remote development tools and projects (VSCode, JetBrains Fleet, Theia, etc.) I felt wanting a way to quickly spin up machines from a predefined config.

I wanted something that would provide a base, but allowed users to extend to their liking, so solutions like Gitpod/Codespaces/Cloud9 were not enough.

## Usage

- Create instance config in `~/revel.yml` like

```yaml
default:
  name: "foo"
  description: "Primary remote development machine"
  ami: ami-05e155ca52886ffe4
  user: ubuntu
  public: true
  size: "t3.micro"
  disk:
    size: 10
    type: "IO1"
  backups: true
  init:
    - files:
        - ~/.yarnrc:/tmp/.yarnrc
    - run: "ls -lah"
    - run: "ls -lah /tmp"
    - files:
        - ~/.other:/tmp/files
```

- Execute `revel create`
- Execute `revel provision`

## Inspiration / Similar Projects

- [Vagrant](https://www.vagrantup.com/)
- [Gitpod](https://www.gitpod.io/)
- [Codespaces](https://github.com/features/codespaces)
- [docker-machine](https://github.com/docker/machine)
