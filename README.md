# Stopro
**Sto**p **pro**crastinating and get work done!

## About
Stopro is simple utility which will help you with self control and build work ethic.
When you activate *self control session* all distracting pages will be blocked. List of
distracting pages is fully configurable. This can help you focus and stop wasting time.

## Commands
- `start` - starts self control session
- `stop` - stops self control session
- `status` - prints session status (WIP)
- `config` - opens config file in editor

## Options
- `-s`,`--silent` - silent mode
- `-c`,`--config` - use custom config file path
- `-h`,`--help`   - shows help

## Configuration
Default configuration path is `/etc/stopro/conf.yml` but you cat set your own with `-c`
option.

Example config:
```
# Sites forbidden during self control sessions (without https and www) 
forbidden_sites:
  - youtube.com
  - instagram.com
  - facebook.com
  - tiktok.com
  - thehackernews.com
  - netflix.com
```

## License
published under GPLv3 license.
