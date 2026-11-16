# Suraj approved retaining the one-off EXP-GENERATOR resources. Their original
# resource declarations are not present in the repository. These removed blocks
# deliberately release the old shared/test state addresses without destroying
# the AWS resources. After apply they are no longer managed by this root.
removed {
  from = aws_ami.eval_generator_recovery

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_ebs_snapshot.eval_generator_recovery

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_iam_instance_profile.eval_generator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_iam_role.eval_generator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_iam_role_policy.eval_generator_operator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_iam_role_policy_attachment.eval_generator_ssm

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_instance.eval_generator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_s3_bucket.eval_generator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_s3_bucket_lifecycle_configuration.eval_generator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_s3_bucket_ownership_controls.eval_generator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_s3_bucket_policy.eval_generator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_s3_bucket_public_access_block.eval_generator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_s3_bucket_server_side_encryption_configuration.eval_generator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_s3_bucket_versioning.eval_generator

  lifecycle {
    destroy = false
  }
}

removed {
  from = aws_security_group.eval_generator

  lifecycle {
    destroy = false
  }
}

# Keep the previous API revision registered for rollback; manage the new image
# under a fresh Terraform address instead of deregistering the old revision.
removed {
  from = aws_ecs_task_definition.api

  lifecycle {
    destroy = false
  }
}
