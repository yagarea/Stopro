# ![Stopro](https://blackblog.cz/assets/img/projects/stopro.svg)

<p align="center">
<b>Sto</b>p <b>pro</b>crastinating and get work done!
</p>

Stopro is simple utility which will help you with self control and build work ethic.
When you activate *self control session* all distracting pages will be blocked. List of
distracting pages is fully configurable. This can help you focus and stop wasting time.


## Commands
- `start`           - starts self control session
- `stop`            - stops self control session
- `lock`            - lock ongoing self control session
- `status`          - print info about current session
- `stats`           - print statistics about usage and time saving
- `config`          - opens configuration file in editor
- `clear-history`   - remove all logs and usage history


## Locking
Self control sessions have lock mechanism. You can set any amount of time in which
self control session can not be turn of. You set time as number and time unit.

- `s` - seconds
- `m` - minutes
- `h` - hours
- `d` - days

Example usages:
- `stopro start --lock 15m`
- `stopro start --lock 1d`
- `stopro lock 30m`
- `stopro lock 3h`


## Stats and achievements
You can measure your work ethic with statistics and challenge your self with achievements.

![Stats](https://jc.ggu.cz/static/stopro-screenshot.png)

## Options
- `-s`,`--silent` - silent mode
- `-c`,`--config` - use custom configuration file path
- `-h`,`--help`   - shows help


## Configuration
Default configuration path is `/etc/stopro/conf.yml` but you cat set your own with `-c`
option.

Example config:
```yml
# Sites forbidden during self control sessions (without https and www) 
forbidden_sites:
  - youtube.com
  - instagram.com
  - facebook.com
  - tiktok.com
  - thehackernews.com
  - reddit.com
  - netflix.com
```

## About
If you find any bug please create issue. Same goes for feature requests. I am also open
to pull requests.

Published under [GPLv3 license](https://www.gnu.org/licenses/gpl-3.0.en.html).
