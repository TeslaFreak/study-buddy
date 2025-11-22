#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { StudyBuddyStack } from '../lib/study-buddy-stack';

const app = new cdk.App();
new StudyBuddyStack(app, 'StudyBuddyStack', {
  /* You can set stack props here */
});
