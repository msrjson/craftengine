---
id: "20261003-231656"
title: Choose source-derived ergonomics improvements for Craft users and coding agents
type: decision
priority: 2
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-03T23:16:56Z
updated_at: 2026-10-03T23:18:24Z
source: Owner-corrected GitHub source comparison for human and coding-agent ergonomics
touches: []
---

## Problem

The initial market study misunderstood the request. The owner clarified that GitHub source implementations must be confronted with Craft source to find ways to make application development easier for humans and coding agents. This task records the corrected technical review and proposal order.

## Evidence

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

### Method and scope

Read 25 successfully downloaded source files across the eleven previously named frameworks and Laravel Boost. Each repository is pinned to the SHA and commit date below; downloads were checked against SHA-256. This is a targeted implementation review of generators, injection, request binding and diagnostics, not a full-repository audit or an upstream runtime test. Selected development branches are not asserted to be latest stable releases. AdonisJS and Masonite default branches were checked explicitly after older branch names were found to be stale. Failed guessed paths (404) were excluded from the evidence.

The question is: which source mechanisms reduce steps, ambiguous choices, manual edits and discovery effort for a human or coding agent using Craft? Proposed gains remain hypotheses until consumer trials. No market ranking, feature scores or cross-runtime speed claims inform these suggestions.

### Source-to-Craft comparison

**Laravel.** [laravel/framework: public function handle()](https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Console/GeneratorCommand.php#L154); [laravel/framework: afterResolving(](https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Foundation/Providers/FormRequestServiceProvider.php#L29); [laravel/framework: public function currentlyResolving()](https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Container/Container.php#L1656)

Reserved-name/collision checks precede single-file writes; FormRequest resolves through validation hooks; container tracks active resolution. Reuse Craft typed request binding and introduce a shared generation preflight. Do not copy implicit global behavior or destructive commands.

**Symfony.** [symfony/symfony: private function createTypeAlternatives(](https://github.com/symfony/symfony/blob/9493f3e814d1cf270f8dcb95c58e44c56de14a89/src/Symfony/Component/DependencyInjection/Compiler/AutowirePass.php#L657); [symfony/symfony: public function complete(](https://github.com/symfony/symfony/blob/9493f3e814d1cf270f8dcb95c58e44c56de14a89/src/Symfony/Component/Console/Application.php#L404)

Autowire diagnostics enumerate candidate services; command completion consumes registered definitions. Adapt candidate/chain diagnostics and structured CLI discovery rather than implementing a compiled PHP container.

**Rails.** [rails/rails: def self.hook_for(](https://github.com/rails/rails/blob/4088f9d2ef00f9b85493362fb6f4b2526bd5d314/railties/lib/rails/generators/base.rb#L174); [rails/rails: def expect(](https://github.com/rails/rails/blob/4088f9d2ef00f9b85493362fb6f4b2526bd5d314/actionpack/lib/action_controller/metal/strong_parameters.rb#L779)

Generator hooks compose optional outputs. expect combines permitted input filtering with required structure. Craft already has validated field filtering; improve generated validation conventions and optional behavior-test hooks, not a second input filter.

**Django.** [django/django: def run_checks(](https://github.com/django/django/blob/a461af8ce48762d7ec602260aaff81014ddccbcb/django/core/checks/registry.py#L74); [django/django: def execute(](https://github.com/django/django/blob/a461af8ce48762d7ec602260aaff81014ddccbcb/django/core/management/base.py#L446)

A registry groups checks by tags and separates deployment checks; commands can request preflight categories. Extend Craft doctor rather than replacing its existing code/location/fix model.

**AdonisJS.** [adonisjs/core: async prepare()](https://github.com/adonisjs/core/blob/e1b2357eacc2e8e72e0815abbc5f2e94264acffb/commands/make/controller.ts#L106); [adonisjs/core: createApp(environment:](https://github.com/adonisjs/core/blob/e1b2357eacc2e8e72e0815abbc5f2e94264acffb/src/ignitor/main.ts#L94)

Generation has prepare/run phases, explicit API/resource/action modes and entity descriptors; Ignitor names web/console/test/repl environments. Adapt generation phases/modes, avoiding an unnecessary new application boot abstraction.

**Masonite.** [MasoniteFramework/masonite: if "/" in full_path:](https://github.com/MasoniteFramework/masonite/blob/b86a236c87e888937e77c031fc1ec378514b4632/src/masonite/commands/MakeControllerCommand.py#L28); [MasoniteFramework/masonite: def make(](https://github.com/MasoniteFramework/masonite/blob/b86a236c87e888937e77c031fc1ec378514b4632/src/masonite/container/container.py#L100)

Nested names are split into directory and class leaf, with API/resource/basic templates. Class-based container resolution is familiar to Python users. Its inspected container uses mutable class-level registries: retain Craft instance/context isolation rather than copying that pattern.

**FastAPI.** [fastapi/fastapi: def get_typed_signature(](https://github.com/fastapi/fastapi/blob/5f9fc5c59a9bb54608aa35376715f3ba9708188e/fastapi/dependencies/utils.py#L213); [fastapi/fastapi: class APIRouter(](https://github.com/fastapi/fastapi/blob/5f9fc5c59a9bb54608aa35376715f3ba9708188e/fastapi/routing.py#L2302)

Typed signatures unwrap callables and resolve forward references; typed public router methods are directly inspectable. Apply consistent annotation resolution and editor-visible contracts while retaining Craft FormRequest and ORM conventions.

**NestJS.** [nestjs/nest: public async resolveConstructorParams](https://github.com/nestjs/nest/blob/35142c3eca8edaaf6abc5984d915da2fbd458aa2/packages/core/injector/injector.ts#L311); [nestjs/nest: constructor(@Optional()](https://github.com/nestjs/nest/blob/35142c3eca8edaaf6abc5984d915da2fbd458aa2/packages/common/pipes/validation.pipe.ts#L76)

Injection tracks resolution context and pending cycles; validation has configurable transformation and exception construction. Adapt bounded dependency diagnostics. Do not add another DTO library or silent global coercion when Craft already validates requests.

**Phoenix.** [phoenixframework/phoenix: def run(args)](https://github.com/phoenixframework/phoenix/blob/2ca60ffe811c0e585835cfc309b645c3a4190df1/lib/mix/tasks/phx.gen.context.ex#L112); [phoenixframework/phoenix: def generator_paths](https://github.com/phoenixframework/phoenix/blob/2ca60ffe811c0e585835cfc309b645c3a4190df1/lib/mix/phoenix.ex#L200)

Context generation builds a file list and checks conflicts before copying, supports schema/context options, generates tests and uses template search paths. Adapt preflight, scoped outputs and project-owned templates; context generation alone does not justify adopting Elixir processes or LiveView.

**Spring Boot.** [spring-projects/spring-boot: public class FailureAnalysis](https://github.com/spring-projects/spring-boot/blob/f6142c9f47591b70949391d1848c1f81503006db/core/spring-boot/src/main/java/org/springframework/boot/diagnostics/FailureAnalysis.java#L27); [spring-projects/spring-boot: interface FailureAnalyzer](https://github.com/spring-projects/spring-boot/blob/f6142c9f47591b70949391d1848c1f81503006db/core/spring-boot/src/main/java/org/springframework/boot/diagnostics/FailureAnalyzer.java#L29)

FailureAnalyzer produces FailureAnalysis with description/action/cause. Craft Finding already has messages and fixes; extend that format to dependency failures and categorized preflight, without reproducing Actuator as a new subsystem.

**ASP.NET Core.** [dotnet/aspnetcore: private static Expression CreateArgument(](https://github.com/dotnet/aspnetcore/blob/dc8b384c43e5578b9dbb476ce15c66c04423ab91/src/Http/Http.Extensions/src/RequestDelegateFactory.cs#L700)

RequestDelegateFactory resolves typed binding sources and records parameter metadata while building delegates. Borrow explicit binding descriptions for diagnosis/introspection; do not add runtime model inference based on guesses or C# expression compilation.

**Laravel Boost (adjacent tooling).** [laravel/boost: class ApplicationInfo](https://github.com/laravel/boost/blob/97b8da0cb8c2c1da75531a36e34adaa313a64afc/src/Mcp/Tools/ApplicationInfo.php#L17)

ApplicationInfo is marked read-only and returns versions/package inventory from the actual app. Provide bounded local project/service/CLI inspection before considering MCP; static generic llms files are not equivalent to current project facts.

### Craft findings

- Partial generation before later conflict checks; existing pretend mode is not full preflight.
- Generated async/manual-validation actions differ from the supported synchronous ORM and typed FormRequest conventions; kernel runs coroutines in worker threads, so no main-event-loop blocking defect is claimed.
- Constructor and route annotation evaluation diverge.
- Doctor has useful structured findings but a fixed check list.
- Dynamic facade signatures and generic static agent files make correct APIs harder to discover.
- CRUD combines API and HTML output without a consumer-selected mode.
- Nested maker names fail identifier checks in an isolated source probe.

### Pinned source manifest

The full manifest is included so evidence survives the temporary download directory. Only metadata and original analysis are committed; foreign source files remain outside this repository.

```json
[
  {
    "repo": "laravel/framework",
    "ref": "13.x",
    "sha": "2c3294632cd68cbe35eaaa6f34fdd97087934098",
    "commit_date": "2026-10-02T20:21:38Z",
    "files": [
      {
        "path": "src/Illuminate/Console/GeneratorCommand.php",
        "bytes": 14266,
        "sha256": "30602de746d33cf0e37f7e438e34953db5b7e6156dc4c6ddfe3573798a87462f",
        "url": "https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Console/GeneratorCommand.php"
      },
      {
        "path": "src/Illuminate/Foundation/Providers/FormRequestServiceProvider.php",
        "bytes": 950,
        "sha256": "94404a02b3001fd0f30f1317bb61d0f99b246d8a189fb2f58a2950f63627416e",
        "url": "https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Foundation/Providers/FormRequestServiceProvider.php"
      },
      {
        "path": "src/Illuminate/Container/Container.php",
        "bytes": 53736,
        "sha256": "8bbfbc5955205f817106077355a493952e685bc376653236a7188f20ff634ea8",
        "url": "https://github.com/laravel/framework/blob/2c3294632cd68cbe35eaaa6f34fdd97087934098/src/Illuminate/Container/Container.php"
      }
    ]
  },
  {
    "repo": "symfony/symfony",
    "ref": "7.3",
    "sha": "9493f3e814d1cf270f8dcb95c58e44c56de14a89",
    "commit_date": "2026-01-28T10:33:21Z",
    "files": [
      {
        "path": "src/Symfony/Component/Console/Application.php",
        "bytes": 48187,
        "sha256": "e27802416be9fd7e59f2943bc3b55be684471a744727c996f377f020e3bb31c5",
        "url": "https://github.com/symfony/symfony/blob/9493f3e814d1cf270f8dcb95c58e44c56de14a89/src/Symfony/Component/Console/Application.php"
      },
      {
        "path": "src/Symfony/Component/DependencyInjection/Compiler/AutowirePass.php",
        "bytes": 33303,
        "sha256": "7330eb2a63fc15f4463de4c0911a50fcd86419078b73ff3d697dadcf8c099c84",
        "url": "https://github.com/symfony/symfony/blob/9493f3e814d1cf270f8dcb95c58e44c56de14a89/src/Symfony/Component/DependencyInjection/Compiler/AutowirePass.php"
      }
    ]
  },
  {
    "repo": "rails/rails",
    "ref": "main",
    "sha": "4088f9d2ef00f9b85493362fb6f4b2526bd5d314",
    "commit_date": "2026-10-03T19:04:10Z",
    "files": [
      {
        "path": "railties/lib/rails/generators/base.rb",
        "bytes": 15677,
        "sha256": "c5344d30bcc95577376c5b13a87aa4ae41378051ec7c96cafcbabba9e49112bd",
        "url": "https://github.com/rails/rails/blob/4088f9d2ef00f9b85493362fb6f4b2526bd5d314/railties/lib/rails/generators/base.rb"
      },
      {
        "path": "actionpack/lib/action_controller/metal/strong_parameters.rb",
        "bytes": 61738,
        "sha256": "32f5d2f8b17be8423b93cc1d66687958881d403feabd27be80442ddcd88e75c3",
        "url": "https://github.com/rails/rails/blob/4088f9d2ef00f9b85493362fb6f4b2526bd5d314/actionpack/lib/action_controller/metal/strong_parameters.rb"
      }
    ]
  },
  {
    "repo": "django/django",
    "ref": "main",
    "sha": "a461af8ce48762d7ec602260aaff81014ddccbcb",
    "commit_date": "2026-10-03T15:23:23Z",
    "files": [
      {
        "path": "django/core/checks/registry.py",
        "bytes": 3898,
        "sha256": "376ea093d729511f795b15b7bb3ddec23dbbf77a458772dc5bee224fd0cf906c",
        "url": "https://github.com/django/django/blob/a461af8ce48762d7ec602260aaff81014ddccbcb/django/core/checks/registry.py"
      },
      {
        "path": "django/core/management/base.py",
        "bytes": 25221,
        "sha256": "bad40932e2d8bd03d9baa83179dae6cde4fba94ec9a4b4e342b5f8d1e2e5a1be",
        "url": "https://github.com/django/django/blob/a461af8ce48762d7ec602260aaff81014ddccbcb/django/core/management/base.py"
      }
    ]
  },
  {
    "repo": "adonisjs/core",
    "ref": "7.x",
    "sha": "e1b2357eacc2e8e72e0815abbc5f2e94264acffb",
    "commit_date": "2026-10-01T10:03:47Z",
    "files": [
      {
        "path": "commands/make/controller.ts",
        "bytes": 4093,
        "sha256": "743b288b9b4cff3c5a4465f976752ddc71ec8db7de3889ac6330e006fd189c79",
        "url": "https://github.com/adonisjs/core/blob/e1b2357eacc2e8e72e0815abbc5f2e94264acffb/commands/make/controller.ts"
      },
      {
        "path": "src/ignitor/main.ts",
        "bytes": 3794,
        "sha256": "a8e7ce07c28fbee76301f857b404ded96d480401f441b3346ac57dc3b8135387",
        "url": "https://github.com/adonisjs/core/blob/e1b2357eacc2e8e72e0815abbc5f2e94264acffb/src/ignitor/main.ts"
      },
      {
        "path": "stubs/make/controller/actions.stub",
        "bytes": 431,
        "sha256": "a78695a525d32991440718335ca22216e3cab9e79e18558b7912da05e38671cf",
        "url": "https://github.com/adonisjs/core/blob/e1b2357eacc2e8e72e0815abbc5f2e94264acffb/stubs/make/controller/actions.stub"
      }
    ]
  },
  {
    "repo": "MasoniteFramework/masonite",
    "ref": "4.0",
    "sha": "b86a236c87e888937e77c031fc1ec378514b4632",
    "commit_date": "2026-06-07T17:52:11Z",
    "files": [
      {
        "path": "src/masonite/commands/MakeControllerCommand.py",
        "bytes": 2865,
        "sha256": "e658347dd07885ff8eca83b9539b33d8e9b891c1a2ecbcf9c16c9dc78cab89e1",
        "url": "https://github.com/MasoniteFramework/masonite/blob/b86a236c87e888937e77c031fc1ec378514b4632/src/masonite/commands/MakeControllerCommand.py"
      },
      {
        "path": "src/masonite/container/container.py",
        "bytes": 16946,
        "sha256": "b7aeb8a2b828db30b868226130e955078d46526a0e25639d18cb5b4257dbf453",
        "url": "https://github.com/MasoniteFramework/masonite/blob/b86a236c87e888937e77c031fc1ec378514b4632/src/masonite/container/container.py"
      },
      {
        "path": "tests/core/foundation/test_container.py",
        "bytes": 4849,
        "sha256": "344fd8140499fd064ed032ea8f34476f843b03c6726bcf3a134762e057ff7e15",
        "url": "https://github.com/MasoniteFramework/masonite/blob/b86a236c87e888937e77c031fc1ec378514b4632/tests/core/foundation/test_container.py"
      }
    ]
  },
  {
    "repo": "fastapi/fastapi",
    "ref": "master",
    "sha": "5f9fc5c59a9bb54608aa35376715f3ba9708188e",
    "commit_date": "2026-10-02T11:36:36Z",
    "files": [
      {
        "path": "fastapi/dependencies/utils.py",
        "bytes": 39180,
        "sha256": "13693375ab95e32424e5434c21f928463634af5ee1261cf3e04031381bdf47d9",
        "url": "https://github.com/fastapi/fastapi/blob/5f9fc5c59a9bb54608aa35376715f3ba9708188e/fastapi/dependencies/utils.py"
      },
      {
        "path": "fastapi/routing.py",
        "bytes": 259409,
        "sha256": "6d8beeb5642f477d7076ec8bf58c57f79f131e2bc8e6bfd5b90224e1ba859ec2",
        "url": "https://github.com/fastapi/fastapi/blob/5f9fc5c59a9bb54608aa35376715f3ba9708188e/fastapi/routing.py"
      }
    ]
  },
  {
    "repo": "nestjs/nest",
    "ref": "master",
    "sha": "35142c3eca8edaaf6abc5984d915da2fbd458aa2",
    "commit_date": "2026-10-02T12:07:21Z",
    "files": [
      {
        "path": "packages/core/injector/injector.ts",
        "bytes": 42082,
        "sha256": "057a38802f466b918bf4a98633777942e65debad6bdeddc4a84bfe5e9b4db679",
        "url": "https://github.com/nestjs/nest/blob/35142c3eca8edaaf6abc5984d915da2fbd458aa2/packages/core/injector/injector.ts"
      },
      {
        "path": "packages/common/pipes/validation.pipe.ts",
        "bytes": 13221,
        "sha256": "e5f1b9ca2769521fec8d41710b940e382c5263214cece95dccb779bad36897c8",
        "url": "https://github.com/nestjs/nest/blob/35142c3eca8edaaf6abc5984d915da2fbd458aa2/packages/common/pipes/validation.pipe.ts"
      }
    ]
  },
  {
    "repo": "phoenixframework/phoenix",
    "ref": "main",
    "sha": "2ca60ffe811c0e585835cfc309b645c3a4190df1",
    "commit_date": "2026-10-02T10:52:42Z",
    "files": [
      {
        "path": "lib/mix/tasks/phx.gen.context.ex",
        "bytes": 14760,
        "sha256": "c7c6dc0e75b25769db626143ad37d43b9c45234190e13a6352b0a6629e05b73e",
        "url": "https://github.com/phoenixframework/phoenix/blob/2ca60ffe811c0e585835cfc309b645c3a4190df1/lib/mix/tasks/phx.gen.context.ex"
      },
      {
        "path": "lib/mix/phoenix.ex",
        "bytes": 11465,
        "sha256": "10170067eb8bc4561c10b3b484c1ff7b427fc49e280b2e131683cd1a81d246d7",
        "url": "https://github.com/phoenixframework/phoenix/blob/2ca60ffe811c0e585835cfc309b645c3a4190df1/lib/mix/phoenix.ex"
      }
    ]
  },
  {
    "repo": "spring-projects/spring-boot",
    "ref": "main",
    "sha": "f6142c9f47591b70949391d1848c1f81503006db",
    "commit_date": "2026-10-02T17:22:28Z",
    "files": [
      {
        "path": "core/spring-boot/src/main/java/org/springframework/boot/diagnostics/FailureAnalyzer.java",
        "bytes": 1200,
        "sha256": "f4234d5178c06ef80588d4b9514f3584c3a4ce14ca2da97afa3cde1a0d419784",
        "url": "https://github.com/spring-projects/spring-boot/blob/f6142c9f47591b70949391d1848c1f81503006db/core/spring-boot/src/main/java/org/springframework/boot/diagnostics/FailureAnalyzer.java"
      },
      {
        "path": "core/spring-boot/src/main/java/org/springframework/boot/diagnostics/FailureAnalysis.java",
        "bytes": 1935,
        "sha256": "e6a0da7d24fb2cf146fe97223a8ad38639e0c67eff834b837e7e12880173f21e",
        "url": "https://github.com/spring-projects/spring-boot/blob/f6142c9f47591b70949391d1848c1f81503006db/core/spring-boot/src/main/java/org/springframework/boot/diagnostics/FailureAnalysis.java"
      }
    ]
  },
  {
    "repo": "dotnet/aspnetcore",
    "ref": "main",
    "sha": "dc8b384c43e5578b9dbb476ce15c66c04423ab91",
    "commit_date": "2026-10-03T19:42:14Z",
    "files": [
      {
        "path": "src/Http/Http.Extensions/src/RequestDelegateFactory.cs",
        "bytes": 153970,
        "sha256": "395b4b6e704a9c7bc34e82d78c8ccefd1b0aa3726bda5a275c8d83e9e984360b",
        "url": "https://github.com/dotnet/aspnetcore/blob/dc8b384c43e5578b9dbb476ce15c66c04423ab91/src/Http/Http.Extensions/src/RequestDelegateFactory.cs"
      }
    ]
  },
  {
    "repo": "laravel/boost",
    "ref": "main",
    "sha": "97b8da0cb8c2c1da75531a36e34adaa313a64afc",
    "commit_date": "2026-10-01T02:04:27Z",
    "files": [
      {
        "path": "src/Mcp/Tools/ApplicationInfo.php",
        "bytes": 1597,
        "sha256": "24c815a5291c7b5c28ad28f844d31b9dd4b4fe1f715d8a7e51ce0a7e3155d73a",
        "url": "https://github.com/laravel/boost/blob/97b8da0cb8c2c1da75531a36e34adaa313a64afc/src/Mcp/Tools/ApplicationInfo.php"
      }
    ]
  }
]
```

## Done when

- [ ] Owner records adopt/defer/reject for each companion suggestion, based on the implementation mechanism and current Craft behavior.
- [ ] Prioritize generation preflight, canonical typed controller templates and nested-name handling before adding broader integrations.
- [ ] Approve consumer verification using the same isolated feature task (generate, import, route, validate, diagnose a deliberate error) for humans and agents; record commands, edited files, failures and manual corrections without claiming measured gains before running it.

## Verify

```bash
python3 .claude/rules/lint_backlog.py
rg -n 'owner ruling:' backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md
git diff --check
```

These verify queue structure and a future owner ruling, not an implemented feature. Verify the Done when decisions against that ruling. Before approved implementation, create a separately scoped task with exact container test commands for the scenarios listed above. No foreign framework or Craft application behavior tests were run during this source review.


To independently replay the pinned source hash verification (read-only, requires GitHub network access):

```bash
python3 - <<'PYVERIFY'
import hashlib, json, pathlib, re, urllib.request
report = pathlib.Path("backlog/pending/p2-20261003-231656-source-framework-ergonomics-review.md").read_text()
manifest = json.loads(re.search(r"```json\n(.*?)\n```", report, re.S).group(1))
verified = 0
for repository in manifest:
    for item in repository["files"]:
        url = "https://raw.githubusercontent.com/{}/{}/{}".format(
            repository["repo"], repository["sha"], item["path"]
        )
        request = urllib.request.Request(url, headers={"User-Agent": "Craft-source-review"})
        with urllib.request.urlopen(request, timeout=45) as response:
            digest = hashlib.sha256(response.read()).hexdigest()
        assert digest == item["sha256"], item["url"]
        verified += 1
print("Verified source files:", verified)
PYVERIFY
```

Research verification already performed: downloaded source bytes matched all 25 manifest hashes; an isolated AST probe confirmed the nested-name examples. These are source-evidence checks, not application behavior tests. Existing parallel lifecycle changes in kernel.py were inspected and do not alter the cited FormRequest binding or worker-thread coroutine behavior.

## Notes

### Research validation results

- Pinned-source replay command above: passed, 25 remote SHA-256 matches.
- `python3 .claude/rules/lint_backlog.py`: passed after every queue change.
- `git diff --check`: passed.
- `python3 .claude/rules/lint_language.py <the new tasks, archived tasks and resolutions>`: passed (all changed existing paths listed in the scoped invocation).
- `python3 .claude/rules/lint_language.py` over default workspace roots: failed on pre-existing artifacts outside this research, including `.agents/docs/`, `.claude/Project Reference/` and translated `website/public/`. The gate was not modified or disabled. The existing engine-language-gate-scope backlog item remains the place for scope policy decisions; this research does not claim the whole workspace is language-clean.
- Application and upstream runtime tests: NOT RUN; this change contains source analysis and queue administration only.

### Companion suggestions

- `backlog/pending/p2-20261003-231657-source-generator-plan.md`
- `backlog/pending/p2-20261003-231658-source-controller-conventions.md`
- `backlog/pending/p2-20261003-231659-source-container-resolution.md`
- `backlog/pending/p2-20261003-231700-source-doctor-registry.md`
- `backlog/pending/p2-20261003-231702-source-agent-inspection.md`
- `backlog/pending/p2-20261003-231703-source-typed-facades.md`
- `backlog/pending/p2-20261003-231704-source-crud-modes.md`
- `backlog/pending/p2-20261003-231705-source-generator-names.md`
- `backlog/pending/p3-20261003-231706-source-scaffold-test-hooks.md`

This internal source review supersedes the seven market-oriented tasks from commit ef1e47f, which will be archived as obsolete with explicit resolutions. It does not modify the public market_evaluation.md or resolve the existing third-party-publication decision. Suggested effort and ordering are engineering judgment, not market evidence.

Craft source baseline: `58f510c344f5362de1a4b35f98190ef2147228c7`. Local references were read from the working tree; unrelated existing worktree changes were preserved. Foreign source links use immutable commit SHAs, not moving branches. Findings are static source analysis unless explicitly stated otherwise.

Research does not authorize implementation. Keep autonomous false until the owner decides. No application code was changed. Source-level lessons require adaptation to Python, Craft's runtime and existing safety contracts; no performance or usability multiplier has been measured.

## History

- 2026-10-03T23:16:56Z created by codex (source: owner-corrected GitHub code comparison; suggestion awaiting owner decision)
- 2026-10-03T23:17:08Z linked companion suggestions by codex after completing the pinned source review
- 2026-10-03T23:17:41Z added reproducible pinned-source hash verification and recorded source-probe limits by codex
- 2026-10-03T23:18:24Z recorded source replay, queue and scoped language validation and existing workspace-wide gate failures by codex
