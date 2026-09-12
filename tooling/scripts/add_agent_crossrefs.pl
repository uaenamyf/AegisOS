#!/usr/bin/perl
# @aegis-gen
# date: 2026-07-03
# dev: Claude Code (glm-5.2)
# change: 为各模块 AGENT.md 追加「交叉引用（去哪里找）」段（domain 派生 + 子路径微调；幂等：已存在则跳过）。
#
# 用法:  find . -name AGENT.md -not -path './.git/*' | perl tooling/scripts/add_agent_crossrefs.pl
# 排除根 AGENT.md（已单独维护）。UTF-8 安全。

use strict;
use warnings;
use utf8;

my %spec = (
  agents         => 'developer/specs/08_AGENT_SPEC.md + 03_IMPORT_SPEC.md',
  protocol       => 'developer/specs/04_PROTOCOL_SPEC.md + 06_SCHEMA_SPEC.md',
  backend        => 'developer/specs/05_API_SPEC.md + 10_INTERFACE_BOUNDARY_SPEC.md',
  frontend       => 'developer/specs/05_API_SPEC.md + 12_TECH_STACK_SPEC.md',
  infrastructure => 'developer/specs/01_ARCHITECTURE_SPEC.md + 12_TECH_STACK_SPEC.md',
  observability  => 'developer/specs/01_ARCHITECTURE_SPEC.md + 07_EVENT_SPEC.md',
  data           => 'developer/specs/06_SCHEMA_SPEC.md',
  tooling        => 'developer/specs/09_DEVELOPMENT_SPEC.md',
  developer      => 'developer/specs/09_DEVELOPMENT_SPEC.md（本目录即 SSOT）',
  docs           => 'developer/specs/02_DIRECTORY_SPEC.md',
  tests          => 'developer/specs/09_DEVELOPMENT_SPEC.md',
);
my %has_api = map { $_ => 1 } qw(agents backend frontend infrastructure observability data tooling);
my %plan = (
  agents         => 'developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（红蓝紫角色/记忆/路由）',
  protocol       => 'developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（A1 cyber 类型）',
  infrastructure => 'developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H1 沙箱靶场/端边云）',
  observability  => 'developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H5 评测/回放）',
  data           => 'developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（H2 Neo4j/Qdrant）',
  tooling        => 'developer/specs/plans/14_CYBERDEFENSE_SOLUTION_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（靶场编排/评测脚本）',
  backend        => 'developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（F 攻防端点）',
  frontend       => 'developer/specs/plans/13_FRONTEND_BACKEND_PLAN.md + plans/15_CYBERDEFENSE_TASKS.md（G 攻防视图）',
);
my %data_contract = (
  agents        => 'protocol/message.py（Message）/ protocol/scheduler.py（Task）',
  protocol      => '本层即契约（无 api/，被各域复用）',
  backend       => 'protocol/message.py（Message）/ protocol/scheduler.py（Task）',
  frontend      => 'protocol/ 类型（经 gen_ts_types 生成 frontend/src/protocol/types.ts）',
  observability => 'protocol/event.py（Event）',
  infrastructure=> 'protocol/message.py / protocol/sync.py',
  data          => 'protocol/memory.py（MemoryPacket）/ protocol/graph.py',
);

my $updated = 0;
my $skipped = 0;
while (my $line = <STDIN>) {
  chomp $line;
  $line =~ s{^\./}{};
  my $path = $line;
  next if $path eq 'AGENT.md' || $path eq '';
  my ($domain) = $path =~ m{^([^/]+)/};
  next unless $domain && exists $spec{$domain};

  open my $fh, '<:encoding(UTF-8)', $path or do { warn "skip $path: $!\n"; next; };
  local $/; my $content = <$fh>; close $fh;

  if ($content =~ /## 交叉引用（去哪里找）/) { $skipped++; next; }

  my @lines;
  push @lines, "- **本模块规范**：$spec{$domain}";
  if ($path =~ m{agents/planning/engine/(router|topology)}) {
    push @lines, "- **本模块规范补充**：04_PROTOCOL_SPEC.md §16 低熵稀疏路由（赛事核心）";
  }
  if ($path =~ m{agents/action/execution}) {
    push @lines, "- **本模块规范补充**：11_AI_CODING_SPEC.md（沙箱隔离）";
  }
  if ($path =~ m{agents/memory}) {
    push @lines, "- **本模块规范补充**：08_AGENT_SPEC.md 记忆 + plans/15 B1-B3 压缩/唤醒";
  }
  if ($path =~ m{backend/(services|api)}) {
    push @lines, "- **下游·本模块调谁**：agents/api（RuntimeAPI 编排）+ DI 端口（plans/13 §3）";
  }
  if ($has_api{$domain}) {
    push @lines, "- **API 边界**：$domain/api/ — from $domain.api import ...";
  }
  push @lines, "- **数据契约**：$data_contract{$domain}" if $data_contract{$domain};
  push @lines, "- **相关计划**：$plan{$domain}" if $plan{$domain};

  my $section = "\n## 交叉引用（去哪里找）\n" . join("\n", @lines) . "\n";

  if ($content =~ /^(## 下辖子模块)/m) {
    $content =~ s/^(## 下辖子模块)/$section\n$1/m;
  } else {
    $content =~ s/\s*\z/\n/;
    $content .= $section;
  }

  open my $out, '>:encoding(UTF-8)', $path or do { warn "write $path: $!\n"; next; };
  print $out $content; close $out;
  print "updated: $path\n";
  $updated++;
}
print "summary: updated=$updated skipped=$skipped\n";
