# Default-off preparation only: metric filters observe fixed, privacy-safe log
# codes. An operator must review costs and configure an alert destination before
# deploying; these alarms expose state in CloudWatch but send no notifications.
variable "notification_monitoring_enabled" {
  description = "Prepare notification failure metrics, dashboard and actionless alarms for a reviewed test deployment."
  type        = bool
  default     = false
}

locals {
  notification_monitoring_enabled = local.base_enabled && var.notification_monitoring_enabled
  notification_metrics = {
    work_error = {
      pattern = "\"notification_work_error\""
      metric  = "WorkerErrors"
    }
    terminal_failure = {
      pattern = "\"notification_delivery outcome=terminal_failure\""
      metric  = "TerminalFailures"
    }
    transient_failure = {
      pattern = "\"notification_delivery outcome=transient_failure\""
      metric  = "TransientFailures"
    }
    ambiguous = {
      pattern = "\"notification_delivery outcome=ambiguous\""
      metric  = "AmbiguousDeliveries"
    }
  }
}

resource "aws_cloudwatch_log_metric_filter" "notification" {
  for_each       = local.notification_monitoring_enabled ? local.notification_metrics : {}
  name           = "${local.prefix}-notification-${each.key}"
  log_group_name = aws_cloudwatch_log_group.api[0].name
  pattern        = each.value.pattern
  metric_transformation {
    name      = each.value.metric
    namespace = "CLIP/Test/Notifications"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_metric_alarm" "notification" {
  for_each            = local.notification_monitoring_enabled ? local.notification_metrics : {}
  alarm_name          = "${local.prefix}-notification-${each.key}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = each.value.metric
  namespace           = "CLIP/Test/Notifications"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  actions_enabled     = false
  alarm_description   = "Notification failure count; action destination requires separate review."
}

resource "aws_cloudwatch_dashboard" "notification" {
  count          = local.notification_monitoring_enabled ? 1 : 0
  dashboard_name = "${local.prefix}-notifications"
  dashboard_body = jsonencode({
    widgets = [{
      type   = "metric"
      x      = 0
      y      = 0
      width  = 12
      height = 6
      properties = {
        title  = "Notification failures"
        region = local.region
        period = 300
        stat   = "Sum"
        metrics = [
          ["CLIP/Test/Notifications", "WorkerErrors"],
          ["CLIP/Test/Notifications", "TerminalFailures"],
          ["CLIP/Test/Notifications", "TransientFailures"],
          ["CLIP/Test/Notifications", "AmbiguousDeliveries"],
        ]
      }
    }]
  })
}
