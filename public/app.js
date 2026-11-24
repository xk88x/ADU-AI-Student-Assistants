// State Variables
let isCampusInside = true;
let isRTL = false;
let currentRole = 'student';
let currentToken = 'ADU-9B2F';
let tokenCountdown = 30;
let qrTimerId = null;
let authToken = '';
let currentUser = null;

const DEMO_ACCOUNTS = {
  student: '1084512@students.adu.ac.ae',
  instructor: 'bhutta@adu.ac.ae',
  advisor: 'advisor@adu.ac.ae',
};

const EN_TO_AR = {
  'Student Assistant': 'المساعد الطلابي',
  'Advising & Schedule': 'الإرشاد والجدول',
  'Attendance & QR': 'الحضور ورمز QR',
  'Study & GPA': 'الدراسة والمعدل',
  'Attendance & Rotating QR': 'الحضور ورمز QR المتغير',
  'Lecture Summaries': 'ملخصات المحاضرات',
  'Advisor Workspace': 'مساحة عمل المرشد',
  'Student (Khalid)': 'طالب (خالد)',
  'Instructor (Dr. Bhutta)': 'دكتور (د. بوتا)',
  'Advisor (Dr. Murad)': 'مرشد (د. مراد)',
  'EN / عربي': 'عربي / EN',
  'Clash-Free Schedule Builder': 'منشئ الجدول بلا تعارضات',
  'Next-semester planning with prerequisite and credit-cap checks': 'تخطيط الفصل القادم مع فحص المتطلبات والحد الائتماني',
  'CGPA: 2.35 | Cap: 18 Cr': 'المعدل: 2.35 | الحد: 18 ساعة',
  'Software Engineering (3 Cr)': 'هندسة البرمجيات (3 ساعات)',
  'Operating Systems (3 Cr)': 'نظم التشغيل (3 ساعات)',
  'Computer Networks (3 Cr)': 'شبكات الحاسوب (3 ساعات)',
  'Engineering Ethics (3 Cr)': 'أخلاقيات الهندسة (3 ساعات)',
  'Capstone Project I (3 Cr)': 'مشروع التخرج 1 (3 ساعات)',
  'Prereq: SWE 301 (Completed)': 'المتطلب: SWE 301 (مكتمل)',
  'Prereq: CSC 201 (Completed)': 'المتطلب: CSC 201 (مكتمل)',
  'No prerequisite': 'بدون متطلب سابق',
  'Blocked: Requires SWE 401 prerequisite': 'محجوب: يتطلب اجتياز SWE 401',
  'Selected:': 'المختار:',
  'Cr': 'ساعة',
  'Generate Timetable': 'إنشاء الجدول',
  'Send to Advisor': 'إرسال للمرشد',
  'Smart Advising Bot': 'مرشد التسجيل الذكي',
  'Grounded in ADU Student Handbook': 'مبني على دليل الطالب لجامعة أبوظبي',
  'Refer to Advisor': 'إحالة للمرشد',
  'Ask about probation credit limits, course prerequisites, or WA absence thresholds.': 'اسأل عن حدود ساعات الإنذار، المتطلبات السابقة، أو نسب الغياب WA.',
  'Source: ADU Undergraduate Handbook': 'المصدر: دليل البكالوريوس لجامعة أبوظبي',
  'Ask an advising question...': 'اكتب سؤالك الإرشادي...',
  'Send': 'إرسال',
  'Student Check-In': 'تسجيل حضور الطالب',
  'UAE Law 45/2021': 'قانون الإمارات 45/2021',
  'Location: Inside Campus (Building B)': 'الموقع: داخل الحرم الجامعي (مبنى B)',
  'Location: Outside Campus (1.2 km away)': 'الموقع: خارج الحرم الجامعي (1.2 كم)',
  'Toggle Inside / Outside': 'تبديل داخل / خارج الحرم',
  'Check In by Location': 'تسجيل الحضور بالموقع',
  'QR Fallback': 'التحقق عبر رمز QR',
  'Enter 30s QR Token (e.g. ADU-9B2F)': 'أدخل رمز QR المتغير (مثل ADU-9B2F)',
  'Verify QR': 'التحقق من QR',
  'My Absence Summary': 'ملخص الغياب الخاص بي',
  'Live absence percentage across enrolled courses': 'نسبة الغياب المباشرة في المساقات المسجلة',
  'Refresh': 'تحديث',
  'Approved Lecture PDFs': 'ملفات المحاضرات المعتمدة',
  'Instructor-approved summaries and exam focus timestamps': 'ملخصات معتمدة من المحاضر ونقاط التركيز للامتحان',
  'Audio Deleted <= 1h': 'حذف الصوت <= 1 ساعة',
  'Enrolled Section Summaries': 'ملخصات الشعب المسجلة',
  'Download PDF': 'تحميل PDF',
  'GPA Prediction & Target': 'التنبؤ بالمعدل والهدف',
  'scikit-learn model using coursework and F2 attendance': 'نموذج تنبؤ يعتمد على أعمال الفصل والحضور',
  'No Bias Features': 'بدون ميزات متحيزة',
  'Personal GPA Target:': 'الهدف الشخصي للمعدل:',
  'Current CGPA': 'المعدل التراكمي',
  'Predicted GPA': 'المعدل المتوقع',
  'Personal Target': 'الهدف الشخصي',
  'Instructor Rotating QR': 'رمز QR المتغير للمحاضر',
  'SWE401-11 | Token rotates every 30 seconds': 'SWE401-11 | يتغير الرمز كل 30 ثانية',
  'Rotate QR': 'تدوير الرمز',
  'Active Token:': 'الرمز النشط:',
  'Expires in': 'ينتهي خلال',
  'Display this rotating token on the classroom projector for students outside GPS accuracy.': 'اعرض هذا الرمز المتغير على شاشة القاعة للطلاب خارج نطاق GPS.',
  'Live Section Roster': 'قائمة الشعبة المباشرة',
  'SWE401-11 | Correct student attendance status': 'SWE401-11 | تعديل حالة حضور الطلاب',
  'Present': 'حاضر',
  'Absent': 'غائب',
  'Upload Lecture Recording': 'رفع تسجيل المحاضرة',
  'Transcribe locally and delete raw audio within 1 hour': 'تفريغ نصي محلي وحذف الصوت خلال ساعة',
  'Section ID': 'رقم الشعبة',
  'Lecture Date': 'تاريخ المحاضرة',
  'Topic / Notes Hint': 'موضوع المحاضرة / ملاحظات',
  'Audio File (Optional)': 'ملف صوتي (اختياري)',
  'Upload & Generate Draft': 'رفع وإنشاء مسودة',
  'Lecture Summary Drafts': 'مسودات ملخصات المحاضرات',
  'Approve drafts to publish PDFs to enrolled students': 'اعتمد المسودات لنشر ملفات PDF للطلاب المسجلين',
  'Approve': 'اعتماد',
  'Withdraw': 'سحب',
  'Approved': 'معتمد',
  'Draft': 'مسودة',
  'Student Referrals Queue': 'قائمة إحالات الطلاب',
  'Questions escalated from Smart Advising Bot': 'الأسئلة المحالة من مرشد التسجيل الذكي',
  'At-Risk Advisees': 'الطلبة المعرضون للخطر الأكاديمي',
  'Students with CGPA < 2.0 or Predicted GPA < 2.0': 'الطلبة بمعدل تراكمي أو متوقع أقل من 2.0',
  'Schedule Draft Approvals': 'اعتماد مسودات الجداول',
  'Review student timetable drafts and approve or request changes': 'مراجعة مسودات جداول الطلبة واعتمادها أو طلب تعديلات',
  'Request Changes': 'طلب تعديلات',
  'Optional review comment...': 'ملاحظة المراجعة (اختياري)...',
  'Abu Dhabi University - ADU AI Student Assistant Portal': 'جامعة أبوظبي - بوابة المساعد الذكي للطلبة',
  'e.g. UML behavioral diagrams and NFR measurability': 'مثال: مخططات السلوك وقابلية قياس المتطلبات',
  'No approved summaries available yet.': 'لا توجد ملخصات معتمدة بعد.',
  'No lecture summaries uploaded yet.': 'لم يتم رفع أي ملخصات محاضرات بعد.',
  'No referrals in queue.': 'لا توجد إحالات في القائمة.',
  'No schedule drafts pending.': 'لا توجد مسودات جداول للمراجعة.',
  'No at-risk advisees found.': 'لا يوجد طلبة معرضون للخطر الأكاديمي حاليا.',
  'No enrolled courses found.': 'لا توجد مساقات مسجلة.',
  'No students in roster.': 'لا يوجد طلاب في الشعبة.',
  'Latest Schedule Draft': 'أحدث مسودة جدول',
  'Advisor Comment': 'ملاحظة المرشد',
  'PENDING_ADVISOR': 'بانتظار المرشد',
  'SUBMITTED': 'مقدم للمراجعة',
  'APPROVED': 'معتمد',
  'CHANGES_REQUESTED': 'مطلوب تعديلات',
};

function t(enText) {
  if (!isRTL) return enText;
  return EN_TO_AR[enText] || enText;
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  const res = await fetch(path, Object.assign({}, options, { headers }));
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res;
}

async function loginAsRole(role) {
  const email = DEMO_ACCOUNTS[role] || DEMO_ACCOUNTS.student;
  const data = await apiFetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password: 'adu12345' }),
  });
  authToken = data.access_token;
  currentUser = data.user;
}

document.addEventListener('DOMContentLoaded', async () => {
  await onRoleChange('student');
});

// Role Switcher: strictly separates Student, Instructor, and Advisor UIs
async function onRoleChange(role) {
  currentRole = role;
  stopQrTimer();

  // Show only nav buttons belonging to the active role
  const navButtons = document.querySelectorAll('#navLinks .nav-btn');
  let firstPaneId = null;
  let firstBtn = null;
  navButtons.forEach(btn => {
    const matches = btn.dataset.role === role;
    btn.classList.toggle('hidden', !matches);
    btn.classList.remove('active');
    if (matches && !firstPaneId) {
      firstPaneId = btn.dataset.pane;
      firstBtn = btn;
    }
  });

  // Hide all panes immediately so nothing from previous role remains visible
  document.querySelectorAll('.demo-pane').forEach(p => p.classList.remove('active'));

  try {
    await loginAsRole(role);
  } catch (e) {
    console.warn('Auth login error:', e.message);
  }

  if (firstPaneId) {
    switchRoleTab(firstPaneId, firstBtn);
  }

  if (role === 'student') {
    updateStudentHeaderInfo();
    await Promise.all([
      loadStudentEligibilityAndDrafts(),
      updateModernGpaPrediction(),
      loadStudentAbsenceSummary(),
      loadStudentSummaries(),
    ]);
  } else if (role === 'instructor') {
    await fetchLiveQr(false);
    startQrTimer();
    await Promise.all([
      loadInstructorRoster(),
      loadInstructorSummaries(),
    ]);
  } else if (role === 'advisor') {
    await Promise.all([
      loadAdvisorReferrals(),
      loadAdvisorDrafts(),
      loadAdvisorAtRisk(),
    ]);
  }
}

function updateStudentHeaderInfo() {
  if (!currentUser) return;
  const cgpa = typeof currentUser.cgpa === 'number' ? currentUser.cgpa : 3.42;
  const maxCr = cgpa < 2.0 ? 12 : 18;
  const capBadge = document.getElementById('liveCapBadge');
  if (capBadge) {
    capBadge.textContent = isRTL
      ? `المعدل: ${cgpa.toFixed(2)} | الحد: ${maxCr} ساعة`
      : `CGPA: ${cgpa.toFixed(2)} | Cap: ${maxCr} Cr`;
  }
  const cgpaEl = document.getElementById('currentCgpaVal');
  if (cgpaEl) cgpaEl.textContent = cgpa.toFixed(2);
  const maxCrEl = document.getElementById('liveMaxCreditsVal');
  if (maxCrEl) maxCrEl.textContent = maxCr;
}

function switchRoleTab(paneId, btnEl) {
  const targetPane = document.getElementById(paneId);
  if (!targetPane || targetPane.dataset.role !== currentRole) return;

  document.querySelectorAll('.demo-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('#navLinks .nav-btn').forEach(b => b.classList.remove('active'));

  targetPane.classList.add('active');
  if (btnEl) {
    btnEl.classList.add('active');
  } else {
    document.querySelectorAll('#navLinks .nav-btn').forEach(b => {
      if (b.dataset.pane === paneId) b.classList.add('active');
    });
  }

  // Refresh live tab data on switch
  if (paneId === 'student-f1') loadStudentEligibilityAndDrafts();
  if (paneId === 'student-f2') loadStudentAbsenceSummary();
  if (paneId === 'student-f3') {
    loadStudentSummaries();
    updateModernGpaPrediction();
  }
  if (paneId === 'instructor-att') {
    fetchLiveQr(false);
    loadInstructorRoster();
  }
  if (paneId === 'instructor-study') loadInstructorSummaries();
  if (paneId === 'advisor-workspace') {
    loadAdvisorReferrals();
    loadAdvisorDrafts();
    loadAdvisorAtRisk();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==================== STUDENT F1: ADVISING & SCHEDULE ====================
async function loadStudentEligibilityAndDrafts() {
  if (currentRole !== 'student') return;
  try {
    const elig = await apiFetch('/api/advisor/eligible');
    const cgpa = typeof elig.current_cgpa === 'number'
      ? elig.current_cgpa
      : (currentUser && typeof currentUser.cgpa === 'number' ? currentUser.cgpa : 3.42);
    const maxCr = typeof elig.max_credits === 'number' ? elig.max_credits : (cgpa < 2.0 ? 12 : 18);

    const capBadge = document.getElementById('liveCapBadge');
    if (capBadge) {
      capBadge.textContent = isRTL
        ? `المعدل: ${cgpa.toFixed(2)} | الحد: ${maxCr} ساعة`
        : `CGPA: ${cgpa.toFixed(2)} | Cap: ${maxCr} Cr`;
    }
    const maxCrEl = document.getElementById('liveMaxCreditsVal');
    if (maxCrEl) maxCrEl.textContent = maxCr;
    const cgpaEl = document.getElementById('currentCgpaVal');
    if (cgpaEl) cgpaEl.textContent = cgpa.toFixed(2);
  } catch (e) {
    console.warn('Eligibility fetch skipped:', e.message);
  }

  const box = document.getElementById('studentDraftStatusBox');
  if (!box) return;
  try {
    const data = await apiFetch('/api/advisor/my-drafts');
    const drafts = Array.isArray(data) ? data : (data.drafts || []);
    if (!drafts.length) {
      box.innerHTML = '';
      return;
    }
    const latest = drafts[0];
    const sections = Array.isArray(latest.section_ids) ? latest.section_ids.join(', ') : (latest.courses_json || '');
    const status = latest.advisor_status || latest.status || 'PENDING_ADVISOR';
    let badgeCls = 'pending';
    if (status === 'APPROVED') badgeCls = 'approved';
    else if (status === 'CHANGES_REQUESTED') badgeCls = 'rejected';

    box.innerHTML = `
      <div class="item-card">
        <div class="item-top">
          <div>
            <div class="item-title">${escapeHTML(t('Latest Schedule Draft'))}: #${latest.draft_id} (${latest.total_credits || 0} ${escapeHTML(t('Cr'))})</div>
            <div class="item-meta">${escapeHTML(sections)}</div>
          </div>
          <span class="status-badge ${badgeCls}">${escapeHTML(t(status))}</span>
        </div>
        ${latest.comment ? `<div class="item-body"><strong>${escapeHTML(t('Advisor Comment'))}:</strong> ${escapeHTML(latest.comment)}</div>` : ''}
      </div>
    `;
  } catch (e) {
    console.warn('My drafts fetch skipped:', e.message);
  }
}

async function sendModernChat() {
  const input = document.getElementById('modernChatInput');
  const text = input.value.trim();
  if (!text) return;

  const chatBox = document.getElementById('modernChatBox');
  const userDiv = document.createElement('div');
  userDiv.className = 'chat-bubble user';
  userDiv.innerHTML = `<div class="bubble-text">${escapeHTML(text)}</div>`;
  chatBox.appendChild(userDiv);
  input.value = '';

  try {
    const data = await apiFetch('/api/advisor/ask', {
      method: 'POST',
      body: JSON.stringify({ question: text, lang: isRTL ? 'ar' : 'en' }),
    });
    const botDiv = document.createElement('div');
    botDiv.className = 'chat-bubble bot';
    const citationHtml = data.citation
      ? `<div class="citation-tag"><strong>${escapeHTML(isRTL ? 'المصدر الرسمي:' : 'Official Source:')}</strong> ${escapeHTML(data.citation)}</div>`
      : '';
    botDiv.innerHTML = `
      <div class="bubble-text">
        ${escapeHTML(data.answer)}
        ${citationHtml}
      </div>
    `;
    chatBox.appendChild(botDiv);
  } catch (e) {
    const errDiv = document.createElement('div');
    errDiv.className = 'chat-bubble bot';
    errDiv.innerHTML = `<div class="bubble-text">Error: ${escapeHTML(e.message)}</div>`;
    chatBox.appendChild(errDiv);
  }
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function referModernAdvisor() {
  try {
    const res = await apiFetch('/api/advisor/refer', {
      method: 'POST',
      body: JSON.stringify({ question: 'Student requested Academic Advisor review (UC-02)' }),
    });
    const alertEl = document.getElementById('scheduleStatusAlert');
    if (alertEl) {
      alertEl.className = 'result-alert success';
      alertEl.textContent = isRTL
        ? `تم إرسال طلب الإحالة #${res.referral_id} (${res.status}) إلى المرشد الأكاديمي.`
        : `Referral Ticket #${res.referral_id} (${res.status}) forwarded to Academic Advisor.`;
      alertEl.classList.remove('hidden');
    }
  } catch (e) {
    alert(`Referral error: ${e.message}`);
  }
}

function updateCreditsCount() {
  const checked = document.querySelectorAll('.modern-checklist input[type="checkbox"]:checked');
  const sum = checked.length * 3;
  const valEl = document.getElementById('liveCreditsVal');
  if (valEl) valEl.textContent = sum;
}

async function generateLiveTimetable(sendToAdvisor) {
  const checked = Array.from(document.querySelectorAll('.modern-checklist input[type="checkbox"]:checked'));
  const course_codes = checked.map(c => c.value);
  const row = document.getElementById('timetableSlotsRow');
  const alertEl = document.getElementById('scheduleStatusAlert');

  try {
    const data = await apiFetch('/api/advisor/schedule', {
      method: 'POST',
      body: JSON.stringify({ course_codes, send_to_advisor: sendToAdvisor }),
    });
    if (!data.ok) {
      alertEl.className = 'result-alert warning';
      alertEl.textContent = data.error;
      alertEl.classList.remove('hidden');
      return;
    }
    const colors = ['c-blue', 'c-green', 'c-purple'];
    row.innerHTML = data.schedule.map((s, idx) => `
      <div class="time-card ${colors[idx % colors.length]}">
        <div class="t-code">${escapeHTML(s.course_code)} (${escapeHTML(s.section_id)})</div>
        <div class="t-slot">${escapeHTML(s.schedule_slot)}</div>
        <div class="t-room">Room ${escapeHTML(s.room_id)}${s.alternatives && s.alternatives.length ? ` | Alt: ${escapeHTML(s.alternatives[0].section_id)}` : ''}</div>
      </div>
    `).join('');
    document.getElementById('liveMaxCreditsVal').textContent = data.max_credits;
    if (sendToAdvisor) {
      alertEl.className = 'result-alert success';
      alertEl.textContent = isRTL
        ? `تم إرسال مسودة الجدول #${data.draft_id} (${data.total_credits} ساعة) للمرشد الأكاديمي.`
        : `Draft #${data.draft_id} (${data.total_credits} Cr) submitted to Advisor for approval.`;
      alertEl.classList.remove('hidden');
      await loadStudentEligibilityAndDrafts();
    } else {
      alertEl.classList.add('hidden');
    }
  } catch (e) {
    alertEl.className = 'result-alert warning';
    alertEl.textContent = e.message;
    alertEl.classList.remove('hidden');
  }
}

// ==================== STUDENT F2: ATTENDANCE & ABSENCE ====================
function toggleLocationSimulation() {
  isCampusInside = !isCampusInside;
  const label = document.getElementById('locLabel');
  if (!label) return;
  const enText = isCampusInside
    ? 'Location: Inside Campus (Building B)'
    : 'Location: Outside Campus (1.2 km away)';
  label.dataset.i18n = enText;
  label.textContent = t(enText);
  label.style.color = isCampusInside ? 'var(--success)' : 'var(--danger)';
}

async function testGeofenceCheckin() {
  const result = document.getElementById('modernGeoResult');
  result.classList.remove('hidden');

  const lat = isCampusInside ? 24.3373 : 24.3500;
  const lon = isCampusInside ? 54.6146 : 54.6300;

  try {
    const data = await apiFetch('/api/attendance/checkin/geo', {
      method: 'POST',
      body: JSON.stringify({ section_id: 'SWE401-11', lat, lon }),
    });
    if (data.checked_in) {
      result.className = 'result-alert success';
      result.innerHTML = `
        <strong>${isRTL ? 'تم تسجيل الحضور (الموقع الجغرافي)' : 'Check-In Verified (Method: GEO)'}</strong><br>
        - ${isRTL ? `المسافة من مبنى B: ${data.distance_m} متر` : `Within Building B geofence (${data.distance_m}m from center)`}.<br>
        - ${escapeHTML(data.privacy)}
      `;
      await loadStudentAbsenceSummary();
    } else {
      result.className = 'result-alert warning';
      result.innerHTML = `
        <strong>${isRTL ? `تم رفض الحضور (خارج النطاق: ${data.distance_m}م)` : `Check-In Denied (Out of Bounds: ${data.distance_m}m)`}</strong><br>
        - ${escapeHTML(data.message)}
      `;
    }
  } catch (e) {
    result.className = 'result-alert warning';
    result.innerHTML = `<strong>${escapeHTML(e.message)}</strong>`;
  }
}

async function testQrCheckin() {
  const input = document.getElementById('modernQrInput');
  const token = input.value.trim().toUpperCase();
  const result = document.getElementById('modernQrResult');
  result.classList.remove('hidden');

  try {
    const data = await apiFetch('/api/attendance/checkin/qr', {
      method: 'POST',
      body: JSON.stringify({ section_id: 'SWE401-11', token }),
    });
    result.className = 'result-alert success';
    result.innerHTML = `
      <strong>${isRTL ? 'تم تسجيل الحضور (رمز QR)' : 'Check-In Verified (Method: QR)'}</strong><br>
      - ${isRTL ? `تم التحقق من الرمز` : `Validated token`} <code>${escapeHTML(data.token)}</code>.
    `;
    input.value = '';
    await loadStudentAbsenceSummary();
  } catch (e) {
    result.className = 'result-alert warning';
    result.innerHTML = `<strong>${escapeHTML(e.message)}</strong>`;
  }
}

async function loadStudentAbsenceSummary() {
  const container = document.getElementById('studentAbsenceList');
  if (!container || currentRole !== 'student' || !currentUser) return;

  try {
    const studentId = currentUser.user_id || 1;
    const data = await apiFetch(`/api/attendance/summary/${studentId}`);
    const courses = data.courses || [];
    if (!courses.length) {
      container.innerHTML = `<div class="empty-state">${escapeHTML(t('No enrolled courses found.'))}</div>`;
      return;
    }
    container.innerHTML = courses.map(c => {
      const pct = Number(c.absence_pct || 0);
      let cls = 'ok';
      if (pct >= 20) cls = 'danger';
      else if (pct >= 10) cls = 'warn';
      const barWidth = Math.min(100, Math.round((pct / 30) * 100));
      return `
        <div class="abs-item">
          <div class="abs-top">
            <span>${escapeHTML(c.course_code)} (${escapeHTML(c.section_id)})</span>
            <span>${pct}% (${escapeHTML(c.warning)})</span>
          </div>
          <div class="abs-bar"><div class="abs-fill ${cls}" style="width:${barWidth}%"></div></div>
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = `<div class="empty-state">${escapeHTML(e.message)}</div>`;
  }
}

// ==================== STUDENT F3: APPROVED SUMMARIES & GPA ====================
async function loadStudentSummaries() {
  const container = document.getElementById('studentSummariesList');
  if (!container || currentRole !== 'student') return;

  try {
    const data = await apiFetch('/api/study/summaries');
    const items = data.summaries || [];
    if (!items.length) {
      container.innerHTML = `<div class="empty-state">${escapeHTML(t('No approved summaries available yet.'))}</div>`;
      return;
    }
    container.innerHTML = items.map(item => `
      <div class="item-card">
        <div class="item-top">
          <div>
            <div class="item-title">${escapeHTML(item.section_id)} | ${escapeHTML(item.lecture_date)}</div>
            <div class="item-meta">Summary #${item.summary_id}</div>
          </div>
          <span class="status-badge approved">${escapeHTML(t('Approved'))}</span>
        </div>
        <ul class="focus-list">
          ${(item.exam_focus || []).map(f => `
            <li><span class="chip-time">${escapeHTML(f.timestamp)}</span> ${escapeHTML(f.topic)}</li>
          `).join('')}
        </ul>
        <div class="item-actions">
          <span></span>
          <button class="btn-primary" onclick="downloadSummaryPdf(${item.summary_id}, '${escapeHTML(item.section_id)}')">${escapeHTML(t('Download PDF'))}</button>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = `<div class="empty-state">${escapeHTML(e.message)}</div>`;
  }
}

async function downloadSummaryPdf(summaryId, sectionId) {
  try {
    const res = await fetch(`/api/study/summary/${summaryId}/pdf`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      alert(`Download denied: ${err.detail}`);
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sectionId}_Summary_${summaryId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert(`Download error: ${e.message}`);
  }
}

async function updateModernGpaPrediction() {
  if (currentRole !== 'student') return;
  const input = document.getElementById('modernTargetGpa');
  const target = parseFloat(input.value) || 3.0;
  const disp = document.getElementById('displayTargetGpa');
  if (disp) disp.textContent = target.toFixed(2);

  const advice = document.getElementById('modernGpaAdvice');
  try {
    const data = await apiFetch('/api/study/gpa/target', {
      method: 'POST',
      body: JSON.stringify({ target_gpa: target }),
    });
    const predEl = document.getElementById('predictedGpaVal');
    if (predEl) predEl.textContent = data.predicted_gpa.toFixed(2);
    if (data.current_cgpa !== undefined) {
      const cgpaEl = document.getElementById('currentCgpaVal');
      if (cgpaEl) cgpaEl.textContent = Number(data.current_cgpa).toFixed(2);
    }

    if (!data.warn_target) {
      advice.style.background = '#f0fdf4';
      advice.style.borderColor = '#bbf7d0';
      advice.innerHTML = `
        <div class="advice-head" style="color:#15803d;">${isRTL ? `على المسار الصحيح (MAE=${data.model_mae})` : `On Track: Target Achieved (MAE=${data.model_mae})`}</div>
        <p>${isRTL
          ? `المعدل المتوقع (${data.predicted_gpa.toFixed(2)}) يحقق هدفك الشخصي (${target.toFixed(2)}).`
          : `Predicted GPA (<strong>${data.predicted_gpa.toFixed(2)}</strong>) meets or exceeds your target of <strong>${target.toFixed(2)}</strong>.`}</p>
      `;
    } else {
      advice.style.background = '#fef2f2';
      advice.style.borderColor = '#fecaca';
      const diff = (target - data.predicted_gpa).toFixed(2);
      const chips = (data.courses || []).map(c =>
        `<div class="adv-chip"><strong>${escapeHTML(c.course_code)}:</strong> ${isRTL ? 'الدرجة المطلوبة' : 'Need'} <strong>${escapeHTML(c.required_grade)}</strong> (CW: ${c.coursework_avg}%, Att: ${c.attendance_pct}%)</div>`
      ).join('');
      advice.innerHTML = `
        <div class="advice-head">${isRTL ? `تنبيه استباقي: أقل من الهدف (${target.toFixed(2)})` : `Proactive Guidance: Below Personal Target (${target.toFixed(2)})`}</div>
        <p>${isRTL
          ? `المعدل المتوقع ${data.predicted_gpa.toFixed(2)} (أقل بـ ${diff} من الهدف; MAE=${data.model_mae}). الدرجات المطلوبة:`
          : `Predicted GPA is <strong>${data.predicted_gpa.toFixed(2)}</strong> (${diff} below target; scikit-learn MAE=${data.model_mae}). Required course grades:`}</p>
        <div class="advice-grades">${chips}</div>
      `;
    }
  } catch (e) {
    console.warn('GPA update skipped:', e.message);
  }
}

// ==================== INSTRUCTOR: QR, ROSTER & SUMMARIES ====================
async function fetchLiveQr(rotate) {
  if (currentRole !== 'instructor') return;
  try {
    const data = await apiFetch(`/api/attendance/qr/SWE401-11?rotate=${rotate}`);
    currentToken = data.token;
    tokenCountdown = data.expires_in;
    const d1 = document.getElementById('modernQrDisplay');
    const d2 = document.getElementById('tokenStr');
    const d3 = document.getElementById('tokenSeconds');
    if (d1) d1.textContent = currentToken;
    if (d2) d2.textContent = currentToken;
    if (d3) d3.textContent = tokenCountdown;
  } catch (e) {
    console.warn('QR fetch error:', e.message);
  }
}

function manualRotateToken() {
  if (currentRole === 'instructor') {
    fetchLiveQr(true);
  }
}

function startQrTimer() {
  stopQrTimer();
  qrTimerId = setInterval(() => {
    if (currentRole !== 'instructor') {
      stopQrTimer();
      return;
    }
    tokenCountdown--;
    if (tokenCountdown <= 0) {
      fetchLiveQr(true);
    } else {
      const el = document.getElementById('tokenSeconds');
      if (el) el.textContent = tokenCountdown;
    }
  }, 1000);
}

function stopQrTimer() {
  if (qrTimerId) {
    clearInterval(qrTimerId);
    qrTimerId = null;
  }
}

async function loadInstructorRoster() {
  const container = document.getElementById('instructorRosterList');
  if (!container || currentRole !== 'instructor') return;

  try {
    const data = await apiFetch('/api/attendance/roster/SWE401-11');
    const roster = data.roster || [];
    if (!roster.length) {
      container.innerHTML = `<div class="empty-state">${escapeHTML(t('No students in roster.'))}</div>`;
      return;
    }
    container.innerHTML = roster.map(r => {
      const statusCls = r.latest_status === 'PRESENT' ? 'present' : 'absent';
      return `
        <div class="item-card">
          <div class="item-top">
            <div>
              <div class="item-title">${escapeHTML(r.full_name)} (ID: ${r.student_id})</div>
              <div class="item-meta">${isRTL ? 'الطريقة' : 'Method'}: ${escapeHTML(r.method)} | ${isRTL ? 'الغياب' : 'Absence'}: ${r.absence_pct}% (${escapeHTML(r.warning)})</div>
            </div>
            <span class="status-badge ${statusCls}">${escapeHTML(r.latest_status)}</span>
          </div>
          <div class="item-actions">
            <span></span>
            <div class="btn-group">
              <button class="btn-success-sm" onclick="correctStudentAttendance(${r.student_id}, 'PRESENT')">${escapeHTML(t('Present'))}</button>
              <button class="btn-danger-sm" onclick="correctStudentAttendance(${r.student_id}, 'ABSENT')">${escapeHTML(t('Absent'))}</button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = `<div class="empty-state">${escapeHTML(e.message)}</div>`;
  }
}

async function correctStudentAttendance(studentId, status) {
  const alertEl = document.getElementById('instructorRosterStatus');
  try {
    await apiFetch('/api/attendance/correct', {
      method: 'POST',
      body: JSON.stringify({ section_id: 'SWE401-11', student_id: studentId, status }),
    });
    if (alertEl) {
      alertEl.className = 'result-alert success';
      alertEl.textContent = isRTL
        ? `تم تحديث حالة الطالب #${studentId} إلى ${status}.`
        : `Updated Student #${studentId} attendance to ${status}.`;
      alertEl.classList.remove('hidden');
    }
    await loadInstructorRoster();
  } catch (e) {
    if (alertEl) {
      alertEl.className = 'result-alert warning';
      alertEl.textContent = e.message;
      alertEl.classList.remove('hidden');
    }
  }
}

async function uploadInstructorLecture() {
  if (currentRole !== 'instructor') return;
  const statusEl = document.getElementById('instructorUploadStatus');
  const sectionId = document.getElementById('uploadSectionId').value.trim() || 'SWE401-11';
  const lectureDate = document.getElementById('uploadLectureDate').value.trim() || '2026-11-24';
  const notesHint = document.getElementById('uploadNotesHint').value.trim();
  const audioInput = document.getElementById('uploadAudioFile');

  try {
    const fd = new FormData();
    fd.append('section_id', sectionId);
    fd.append('lecture_date', lectureDate);
    fd.append('notes_hint', notesHint);
    if (audioInput && audioInput.files && audioInput.files[0]) {
      fd.append('audio', audioInput.files[0]);
    }

    const res = await fetch('/api/study/upload', {
      method: 'POST',
      headers: { Authorization: `Bearer ${authToken}` },
      body: fd,
    });
    const up = await res.json();
    if (!res.ok) throw new Error(up.detail || 'Upload failed');

    statusEl.className = 'result-alert success';
    statusEl.textContent = isRTL
      ? `تم إنشاء المسودة #${up.summary_id}. تم حذف الصوت الخام: ${up.audio_deleted}.`
      : `Draft #${up.summary_id} generated. Raw audio deleted: ${up.audio_deleted} (NFR11).`;
    statusEl.classList.remove('hidden');
    await loadInstructorSummaries();
  } catch (e) {
    statusEl.className = 'result-alert warning';
    statusEl.textContent = `Upload error: ${e.message}`;
    statusEl.classList.remove('hidden');
  }
}

async function loadInstructorSummaries() {
  const container = document.getElementById('instructorSummariesList');
  if (!container || currentRole !== 'instructor') return;

  try {
    const data = await apiFetch('/api/study/summaries');
    const items = data.summaries || [];
    if (!items.length) {
      container.innerHTML = `<div class="empty-state">${escapeHTML(t('No lecture summaries uploaded yet.'))}</div>`;
      return;
    }
    container.innerHTML = items.map(item => `
      <div class="item-card">
        <div class="item-top">
          <div>
            <div class="item-title">${escapeHTML(item.section_id)} | ${escapeHTML(item.lecture_date)}</div>
            <div class="item-meta">Summary #${item.summary_id}</div>
          </div>
          <span class="status-badge ${item.approved ? 'approved' : 'draft'}">
            ${escapeHTML(item.approved ? t('Approved') : t('Draft'))}
          </span>
        </div>
        <ul class="focus-list">
          ${(item.exam_focus || []).map(f => `
            <li><span class="chip-time">${escapeHTML(f.timestamp)}</span> ${escapeHTML(f.topic)}</li>
          `).join('')}
        </ul>
        <div class="item-actions">
          <div class="btn-group">
            ${!item.approved ? `<button class="btn-success-sm" onclick="approveInstructorSummary(${item.summary_id}, false)">${escapeHTML(t('Approve'))}</button>` : ''}
            <button class="btn-danger-sm" onclick="approveInstructorSummary(${item.summary_id}, true)">${escapeHTML(t('Withdraw'))}</button>
          </div>
          <button class="btn-secondary" onclick="downloadSummaryPdf(${item.summary_id}, '${escapeHTML(item.section_id)}')">${escapeHTML(t('Download PDF'))}</button>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = `<div class="empty-state">${escapeHTML(e.message)}</div>`;
  }
}

async function approveInstructorSummary(summaryId, withdraw) {
  try {
    const query = withdraw ? '?withdraw=true' : '';
    await apiFetch(`/api/study/approve/${summaryId}${query}`, { method: 'POST' });
    await loadInstructorSummaries();
  } catch (e) {
    alert(`Action failed: ${e.message}`);
  }
}

// ==================== ADVISOR: REFERRALS, DRAFTS, AT-RISK ====================
async function loadAdvisorReferrals() {
  const container = document.getElementById('advisorReferralsList');
  if (!container || currentRole !== 'advisor') return;

  try {
    const data = await apiFetch('/api/advisor/referrals');
    const items = Array.isArray(data) ? data : (data.referrals || []);
    if (!items.length) {
      container.innerHTML = `<div class="empty-state">${escapeHTML(t('No referrals in queue.'))}</div>`;
      return;
    }
    container.innerHTML = items.map(r => {
      const name = r.student_name || r.full_name || `Student #${r.student_id}`;
      const email = r.student_email || r.email || '';
      const status = r.status || 'OPEN';
      return `
        <div class="item-card">
          <div class="item-top">
            <div>
              <div class="item-title">${escapeHTML(name)}${email ? ` (${escapeHTML(email)})` : ''}</div>
              <div class="item-meta">Ticket #${r.referral_id}${r.created_at ? ` | ${escapeHTML(r.created_at)}` : ''}</div>
            </div>
            <span class="status-badge info">${escapeHTML(status)}</span>
          </div>
          <div class="item-body">${escapeHTML(r.question || '')}</div>
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = `<div class="empty-state">${escapeHTML(e.message)}</div>`;
  }
}

async function loadAdvisorAtRisk() {
  const container = document.getElementById('advisorAtRiskList');
  if (!container || currentRole !== 'advisor') return;

  try {
    const data = await apiFetch('/api/advisor/at-risk');
    const items = Array.isArray(data) ? data : (data.students || data.at_risk || []);
    if (!items.length) {
      container.innerHTML = `<div class="empty-state">${escapeHTML(t('No at-risk advisees found.'))}</div>`;
      return;
    }
    container.innerHTML = items.map(s => {
      const name = s.full_name || s.student_name || `Student #${s.student_id || s.user_id}`;
      const email = s.email || s.student_email || '';
      const reasons = Array.isArray(s.reasons) ? s.reasons.join(' | ') : (s.reason || '');
      const cgpa = s.cgpa !== undefined ? Number(s.cgpa).toFixed(2) : '-';
      const pred = s.predicted_gpa !== undefined ? Number(s.predicted_gpa).toFixed(2) : '-';
      return `
        <div class="item-card">
          <div class="item-top">
            <div>
              <div class="item-title">${escapeHTML(name)}${email ? ` (${escapeHTML(email)})` : ''}</div>
              <div class="item-meta">CGPA: ${cgpa} | Predicted: ${pred}</div>
            </div>
            <span class="status-badge danger">AT RISK</span>
          </div>
          ${reasons ? `<div class="item-body">${escapeHTML(reasons)}</div>` : ''}
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = `<div class="empty-state">${escapeHTML(e.message)}</div>`;
  }
}

async function loadAdvisorDrafts() {
  const container = document.getElementById('advisorDraftsList');
  if (!container || currentRole !== 'advisor') return;

  try {
    const data = await apiFetch('/api/advisor/drafts');
    const items = Array.isArray(data) ? data : (data.drafts || []);
    if (!items.length) {
      container.innerHTML = `<div class="empty-state">${escapeHTML(t('No schedule drafts pending.'))}</div>`;
      return;
    }
    container.innerHTML = items.map(d => {
      const name = d.student_name || d.full_name || `Student #${d.student_id}`;
      const email = d.student_email || d.email || '';
      const sections = Array.isArray(d.section_ids) ? d.section_ids.join(', ') : (d.courses_json || '');
      const status = d.advisor_status || d.status || 'PENDING_ADVISOR';
      let badgeCls = 'pending';
      if (status === 'APPROVED') badgeCls = 'approved';
      else if (status === 'CHANGES_REQUESTED') badgeCls = 'rejected';

      return `
        <div class="item-card">
          <div class="item-top">
            <div>
              <div class="item-title">Draft #${d.draft_id} - ${escapeHTML(name)}${email ? ` (${escapeHTML(email)})` : ''}</div>
              <div class="item-meta">${isRTL ? 'الساعات' : 'Credits'}: ${d.total_credits || 0} Cr | ${escapeHTML(sections)}</div>
            </div>
            <span class="status-badge ${badgeCls}">${escapeHTML(status)}</span>
          </div>
          ${d.comment ? `<div class="item-meta">${isRTL ? 'ملاحظة المرشد' : 'Comment'}: ${escapeHTML(d.comment)}</div>` : ''}
          <div class="draft-review-row">
            <input type="text" id="draftComment-${d.draft_id}" placeholder="${escapeHTML(t('Optional review comment...'))}">
            <button class="btn-success-sm" onclick="reviewAdvisorDraft(${d.draft_id}, 'APPROVED')">${escapeHTML(t('Approve'))}</button>
            <button class="btn-danger-sm" onclick="reviewAdvisorDraft(${d.draft_id}, 'CHANGES_REQUESTED')">${escapeHTML(t('Request Changes'))}</button>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = `<div class="empty-state">${escapeHTML(e.message)}</div>`;
  }
}

async function reviewAdvisorDraft(draftId, status) {
  const alertEl = document.getElementById('advisorDraftStatus');
  const commentEl = document.getElementById(`draftComment-${draftId}`);
  const comment = commentEl ? commentEl.value.trim() : '';

  try {
    await apiFetch(`/api/advisor/drafts/${draftId}/review`, {
      method: 'POST',
      body: JSON.stringify({ status, comment }),
    });
    if (alertEl) {
      alertEl.className = 'result-alert success';
      alertEl.textContent = isRTL
        ? `تم تحديث المسودة #${draftId} إلى ${status}.`
        : `Draft #${draftId} marked as ${status}.`;
      alertEl.classList.remove('hidden');
    }
    await loadAdvisorDrafts();
  } catch (e) {
    if (alertEl) {
      alertEl.className = 'result-alert warning';
      alertEl.textContent = e.message;
      alertEl.classList.remove('hidden');
    }
  }
}

// ==================== BILINGUAL EN/AR & RTL ====================
function toggleRTL() {
  isRTL = !isRTL;
  document.documentElement.lang = isRTL ? 'ar' : 'en';
  if (isRTL) document.body.setAttribute('dir', 'rtl');
  else document.body.removeAttribute('dir');

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    el.textContent = t(key);
  });

  document.querySelectorAll('input[placeholder]').forEach(el => {
    if (!el.dataset.enPlaceholder) el.dataset.enPlaceholder = el.placeholder;
    const en = el.dataset.enPlaceholder;
    el.placeholder = t(en);
  });

  // Re-render dynamic lists for the active role so dynamic labels also translate
  if (currentRole === 'student') {
    updateStudentHeaderInfo();
    loadStudentEligibilityAndDrafts();
    loadStudentAbsenceSummary();
    loadStudentSummaries();
    updateModernGpaPrediction();
  } else if (currentRole === 'instructor') {
    loadInstructorRoster();
    loadInstructorSummaries();
  } else if (currentRole === 'advisor') {
    loadAdvisorReferrals();
    loadAdvisorDrafts();
    loadAdvisorAtRisk();
  }
}

function escapeHTML(str) {
  return String(str).replace(/[&<>'"]/g,
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}
